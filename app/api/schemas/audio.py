import uuid
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

# Saída básica (listagem / getById)
class AudioBasic(BaseModel):
    # Identificação e arquivo
    id: uuid.UUID
    rel_path: str
    sha256: Optional[str] = None
    format: Optional[str] = None

    # Propriedades do áudio
    duration_s: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    dataset: Optional[str] = None
    speaker_id: Optional[str] = None
    emotion_label: Optional[str] = None
    split: Optional[str] = None
    augment_pipeline: Optional[str] = None

    # Processamento (geral)
    processing_status: str
    processing_error: Optional[str] = None
    processing_metadata: Optional[Dict[str, Any]] = None

    # Resumo/consenso
    predicted_emotion: Optional[str] = None
    confidence_score: Optional[float] = None

    # === Resultados do modelo 1D ===
    model1d_status: Optional[str] = None
    model1d_predicted_emotion: Optional[str] = None
    model1d_confidence_score: Optional[float] = None
    model1d_probs: Optional[Dict[str, float]] = None
    model1d_segments: Optional[Any] = None
    model1d_metadata: Optional[Dict[str, Any]] = None

    # === Resultados do modelo MultiModal ===
    mm_status: Optional[str] = None
    mm_predicted_emotion: Optional[str] = None
    mm_confidence_score: Optional[float] = None
    mm_probs: Optional[Dict[str, Any]] = None
    mm_segments: Optional[Any] = None
    mm_metadata: Optional[Dict[str, Any]] = None

    # Auditoria
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2

class AudioListResponse(BaseModel):
    items: list[AudioBasic]
    totalRecords: int = Field(..., description="Total de registros que atendem aos filtros (ignora paginação)")

# Entrada para criação
class AudioCreate(BaseModel):
    rel_path: str = Field(..., description="Caminho relativo do arquivo (ex.: datasets/cafe/0001.wav)")
    sha256: Optional[str] = Field(None, min_length=64, max_length=64)
    format: Optional[str] = Field(None, max_length=8)
    duration_s: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    dataset: Optional[str] = Field(None, max_length=64)
    speaker_id: Optional[str] = Field(None, max_length=64)
    emotion_label: Optional[str] = Field(None, max_length=32)
    split: Optional[str] = Field(None, max_length=8)
    augment_pipeline: Optional[str] = None


# Entrada para atualização (PUT)
class AudioUpdate(BaseModel):
    rel_path: str
    sha256: Optional[str] = Field(None, min_length=64, max_length=64)
    format: Optional[str] = Field(None, max_length=8)
    duration_s: Optional[float] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    dataset: Optional[str] = Field(None, max_length=64)
    speaker_id: Optional[str] = Field(None, max_length=64)
    emotion_label: Optional[str] = Field(None, max_length=32)
    split: Optional[str] = Field(None, max_length=8)
    augment_pipeline: Optional[str] = None

class AudioFileSchema(BaseModel):
    id: str
    filename: str
    rel_path: str
    duration_s: float
