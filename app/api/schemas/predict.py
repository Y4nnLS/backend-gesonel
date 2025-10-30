from __future__ import annotations
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class AnalyzeRequest(BaseModel):
    # aceita {"audio_id": "..."} no body e mapeia para o campo id
    id: uuid.UUID = Field(alias="audio_id")
    # modelo opcional (padrão)
    modelo: Optional[str] = "default"

    # Pydantic v2
    model_config = ConfigDict(populate_by_name=True, extra="ignore")

class AnalyzeResponse(BaseModel):
    emotion: str
    confidence: float

class EmotionRecordSchema(BaseModel):
    id: str
    audio_id: str
    modelo: str
    emotion: str
    confidence: float
    analyzed_at: datetime
