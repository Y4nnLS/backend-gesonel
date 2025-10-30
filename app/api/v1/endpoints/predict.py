from fastapi import APIRouter, Query, HTTPException, status, Depends
from typing import List
import uuid
import os
import logging
from sqlalchemy.orm import Session

from app.api.core.db import get_db
from app.api.models.audio_file import AudioFile
from app.api.services.emotion_service import emotion_service
from app.api.websocket import manager

from app.api.schemas.predict import EmotionRecordSchema, AnalyzeRequest, AnalyzeResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["predict"])


@router.get(
    "/getDados",
    response_model=List[EmotionRecordSchema],
    summary="Recupera registros de emoção por modelo",
)
def get_dados(modelo: str = Query(..., description="Nome ou ID do modelo")):
    # TODO: Buscar registros no banco filtrando pelo modelo
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

    # 3) Garantir modelo pronto ANTES de tocar no banco
    if not hasattr(emotion_service, "ensure_ready"):
        # fallback defensivo: se não tiver ensure_ready(), tenta is_ready() ou assume pronto
        try:
            if hasattr(emotion_service, "is_ready") and not emotion_service.is_ready():
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Serviço de reconhecimento de emoção não está pronto",
                )
        except Exception as e:
            raise HTTPException(status_code=503, detail=str(e))
    else:
        try:
            if not emotion_service.ensure_ready():  # retorna False se não carregou
                detail = getattr(emotion_service, "last_error", None) or "Serviço de reconhecimento de emoção não está pronto"
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
        except HTTPException:
            raise
        except Exception as e:
            # erro ao carregar o modelo
            raise HTTPException(status_code=503, detail=str(e))

    # 4) Validar arquivo no disco
    rel_path = "db-stack/audios/" + audio.rel_path
    if not rel_path or not os.path.exists(rel_path):
        # não mexe status se o arquivo sumiu: marca failed explicitamente
        audio.processing_status = "failed"
        audio.processing_error = f"Arquivo não encontrado em rel_path: {rel_path!r}"
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

    # 5) Marca como processing e notifica
    audio.processing_status = "processing"
    audio.processing_error = None
    db.commit()
    try:
        await manager.broadcast_audio_update(str(audio_uuid), "processing", {"rel_path": rel_path})
    except Exception:
        pass

    # 6) Inferência + persistência
    try:
        # tenta passar modelo; se não aceitar, chama sem
        try:
            result = emotion_service.predict_emotion(rel_path, model=(req.modelo or "default"))
        except TypeError:
            result = emotion_service.predict_emotion(rel_path)

        if not isinstance(result, dict):
            raise RuntimeError("Retorno inválido do serviço de emoção (esperado dict)")

        emotion = result.get("emotion")
        confidence = result.get("confidence")

        if emotion is None or confidence is None:
            raise RuntimeError("Retorno do modelo sem 'emotion' ou 'confidence'")

        try:
            confidence = float(confidence)
        except Exception:
            raise RuntimeError(f"Confidence inválido: {confidence!r}")

        metadata = result.get("metadata")

        # persiste
        audio.predicted_emotion = str(emotion)
        audio.confidence_score = confidence
        if hasattr(audio, "processing_metadata"):
            audio.processing_metadata = metadata
        audio.processing_status = "completed"
        db.commit()

        # notifica via WS
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
        # qualquer erro de inferência => failed
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
