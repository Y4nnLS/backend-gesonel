from fastapi import APIRouter, Query, HTTPException, status, Depends
from typing import List, Optional
import uuid
import os
import logging
from sqlalchemy.orm import Session

from app.api.core.db import get_db
from app.api.models.audio_file import AudioFile
from app.api.services.emotion_service import emotion_service
from app.api.websocket import manager

from app.api.schemas.predict import EmotionRecordSchema, AnalyzeRequest, AnalyzeResponse
from app.api.services.models.registry import resolve_models, available_models
from app.api.services.emotion_multi import infer_with_models
from app.api.services.results import save_1d_result, save_mm_result

logger = logging.getLogger(__name__)
router = APIRouter(tags=["predict"])

AUDIO_BASE_DIR = os.getenv("AUDIO_BASE_DIR", "db-stack/audios")

@router.get(
    "/getDados",
    response_model=List[EmotionRecordSchema],
    summary="Recupera registros de emoção por modelo",
)
def get_dados(modelo: str = Query(..., description="Nome ou ID do modelo")):
    dummy = [
        EmotionRecordSchema(
            id="1",
            audio_id="audio-uuid",
            modelo=modelo,
            emotion="felicidade",
            confidence=0.92,
            analyzed_at="2025-09-29T12:00:00Z",
        )
    ]
    return dummy

@router.get("/models", summary="Lista modelos disponíveis")
def list_models():
    return {"models": available_models()}

@router.post(
    "/analyzeAudio",
    response_model=AnalyzeResponse,
    summary="Processa áudio e retorna emoção inferida",
)
async def analyze_audio(req: AnalyzeRequest, db: Session = Depends(get_db)):
    # 1) Busca o áudio
    audio_uuid = req.id
    audio = db.get(AudioFile, audio_uuid)
    if not audio:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Áudio não encontrado")

    # 2) Idempotência
    status_atual = (audio.processing_status or "").lower()
    if status_atual in ("processing", "queued"):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Áudio já está em processamento")

    # 3) Arquivo
    rel_path = os.path.join(AUDIO_BASE_DIR, audio.rel_path or "")
    if not os.path.exists(rel_path):
        audio.processing_status = "failed"
        audio.processing_error = f"Arquivo não encontrado: {rel_path!r}"
        db.commit()
        try:
            await manager.broadcast_audio_update(
                str(audio_uuid),
                "failed",
                {"rel_path": rel_path, "error": audio.processing_error},
            )
        except Exception:
            pass
        raise HTTPException(status_code=404, detail="Arquivo do áudio não encontrado no servidor")

    # 4) Marca processing
    audio.processing_status = "processing"
    audio.processing_error = None
    db.commit()
    try:
        await manager.broadcast_audio_update(str(audio_uuid), "processing", {"rel_path": rel_path})
    except Exception:
        pass
    # 5) Inferência
    try:
        modelos: Optional[List[str]] = req.modelos
        if not modelos and req.modelo:
            modelos = [req.modelo]

        # if modelos:
        #     modelos_resolvidos = resolve_models(modelos)
        #     if not modelos_resolvidos:
        #         raise HTTPException(status_code=400, detail="Nenhum modelo válido informado")
        #     multi = infer_with_models(rel_path, modelos_resolvidos)

        #     tops = [v["top"] for v in multi.values() if isinstance(v, dict) and "top" in v]
        #     top = max(set(tops), key=tops.count) if tops else ""
        #     conf = None
        #     if top:
        #         try:
        #             conf = max(v["scores"][top] for v in multi.values() if "scores" in v and top in v["scores"])
        #         except Exception:
        #             conf = None

        #     audio.predicted_emotion = str(top or "")
        #     audio.confidence_score = float(conf) if conf is not None else None
        #     if hasattr(audio, "processing_metadata"):
        #         audio.processing_metadata = {"multi_model": multi}
        #     audio.processing_status = "completed"
        #     db.commit()

        #     try:
        #         await manager.broadcast_audio_update(
        #             str(audio_uuid), "completed",
        #             {"rel_path": rel_path, "predicted_emotion": top, "confidence_score": conf, "multi": multi},
        #         )
        #     except Exception:
        #         pass

        #     return AnalyzeResponse(emotion=str(top or ""), confidence=float(conf or 0.0))
        if modelos:
            modelos_resolvidos = resolve_models(modelos)
            if not modelos_resolvidos:
                raise HTTPException(status_code=400, detail="Nenhum modelo válido informado")

            # Roda múltiplos modelos
            multi = infer_with_models(rel_path, modelos_resolvidos)
            # multi esperado (flexível):
            # {
            #   "keras_emotion": {"scores": {...}, "top": "happy", "conf": 0.82, "segments": None, "meta": {...}},
            #   "multimodal":    {"scores": {...}, "top": "neutral","conf": 0.74, "segments": [...], "meta": {...}}
            # }

            def get_part(d: dict, key: str, default=None):
                return d.get(key, default) if isinstance(d, dict) else default

            # --- salva 1D (vários aliases aceitáveis) ---
            one_d_key = None
            for k in ("keras_emotion", "cnn1d", "model_1d", "keras_1d"):
                if k in multi: one_d_key = k; break
            if one_d_key:
                _r = multi[one_d_key]
                save_1d_result(
                    db, audio_uuid,
                    probs=get_part(_r, "scores", {}) or {},
                    top_label=get_part(_r, "top"),
                    confidence=get_part(_r, "conf"),
                    segments=get_part(_r, "segments"),
                    metadata={"source": one_d_key, **(get_part(_r, "meta", {}) or {})},
                    status="done",
                )

            # --- salva MultiModal (vários aliases aceitáveis) ---
            mm_key = None
            for k in ("multimodal", "multi_modal", "mm"):
                if k in multi: mm_key = k; break
            if mm_key:
                _r = multi[mm_key]
                save_mm_result(
                    db, audio_uuid,
                    probs=get_part(_r, "scores", {}) or {},
                    top_label=get_part(_r, "top"),
                    confidence=get_part(_r, "conf"),
                    segments=get_part(_r, "segments"),
                    metadata={"source": mm_key, **(get_part(_r, "meta", {}) or {})},
                    status="done",
                )

            # --- consenso que você já fazia ---
            tops = [v.get("top") for v in multi.values() if isinstance(v, dict) and v.get("top")]
            top = max(set(tops), key=tops.count) if tops else ""
            conf = None
            if top:
                try:
                    conf = max(v["scores"][top] for v in multi.values() if "scores" in v and top in v["scores"])
                except Exception:
                    conf = None

            audio.predicted_emotion = str(top or "")
            audio.confidence_score = float(conf) if conf is not None else None
            if hasattr(audio, "processing_metadata"):
                audio.processing_metadata = {"multi_model": multi}
            audio.processing_status = "completed"
            db.commit()

            try:
                await manager.broadcast_audio_update(
                    str(audio_uuid), "completed",
                    {"rel_path": rel_path, "predicted_emotion": top, "confidence_score": conf, "multi": multi},
                )
            except Exception:
                pass

            return AnalyzeResponse(emotion=str(top or ""), confidence=float(conf or 0.0))


        # modo único (Keras)
        if not (hasattr(emotion_service, "is_ready") and emotion_service.is_ready()):
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                                detail="Serviço de reconhecimento de emoção não está pronto")

        result = emotion_service.predict_emotion(rel_path)
        if not isinstance(result, dict):
            raise RuntimeError("Retorno inválido do serviço de emoção (esperado dict)")

        emotion = result.get("emotion")
        confidence = result.get("confidence")
        if emotion is None or confidence is None:
            raise RuntimeError("Retorno do modelo sem 'emotion' ou 'confidence'")

        confidence = float(confidence)
        metadata = result.get("metadata")

        audio.predicted_emotion = str(emotion)
        audio.confidence_score = confidence
        if hasattr(audio, "processing_metadata"):
            audio.processing_metadata = metadata
        audio.processing_status = "completed"
        db.commit()

        try:
            await manager.broadcast_audio_update(
                str(audio_uuid),
                "completed",
                {"rel_path": rel_path, "predicted_emotion": emotion, "confidence_score": confidence},
            )
        except Exception:
            pass

        return AnalyzeResponse(emotion=str(emotion), confidence=confidence)

    except HTTPException:
        raise
    except Exception as e:
        audio.processing_status = "failed"
        audio.processing_error = str(e)
        db.commit()
        try:
            await manager.broadcast_audio_update(
                str(audio_uuid),
                "failed",
                {"rel_path": rel_path, "error": str(e)},
            )
        except Exception:
            pass
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
