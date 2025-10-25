from sqlalchemy import Column, String, Float, DateTime
from app.api.core.db import Base

class EmotionRecordSchema(Base):
    __tablename__ = "emotion_records"

    id = Column(String, primary_key=True, index=True)
    audio_id = Column(String, index=True)
    modelo = Column(String)
    emotion = Column(String)
    confidence = Column(Float)
    analyzed_at = Column(DateTime)