import uuid
from typing import Optional
from pydantic import BaseModel, Field

# Saída básica (listagem / getById)
class AudioBasic(BaseModel):
    id: uuid.UUID
    rel_path: str
    duration_s: Optional[float] = None

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
