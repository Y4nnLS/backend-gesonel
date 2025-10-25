from pydantic import BaseModel

class EmotionRecordSchema(BaseModel):
    id: str
    audio_id: str
    modelo: str
    emotion: str
    confidence: float
    analyzed_at: str

class AnalyzeRequest(BaseModel):
    id: str
    modelo: str

class AnalyzeResponse(BaseModel):
    emotion: str
    confidence: float