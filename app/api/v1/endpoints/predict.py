from fastapi import APIRouter, Query, HTTPException, status
from pydantic import BaseModel
from typing import List
from app.api.schemas.predict import EmotionRecordSchema, AnalyzeRequest, AnalyzeResponse

router = APIRouter(tags=["predict"])

@router.get("/getDados", response_model=List[EmotionRecordSchema], summary="Recupera registros de emoção por modelo")
def get_dados(modelo: str = Query(..., description="Nome ou ID do modelo")):
    # TODO: Buscar registros no banco filtrando pelo modelo
    dummy = [
        EmotionRecordSchema(
            id="1",
            audio_id="audio-uuid",
            modelo=modelo,
            emotion="felicidade",
            confidence=0.92,
            analyzed_at="2025-09-29T12:00:00Z"
        )
    ]
    return dummy

@router.post("/analyzeAudio", response_model=AnalyzeResponse, summary="Processa áudio e retorna emoção inferida")
def analyze_audio(req: AnalyzeRequest):
    # TODO: Buscar áudio pelo req.id, rodar inferência com req.modelo
    if not req.id or not req.modelo:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID ou modelo ausente")
    # Aqui você integraria o pipeline real de inferência
    result = AnalyzeResponse(
        emotion="tristeza",
        confidence=0.85
    )
    return result