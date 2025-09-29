from sqlalchemy.orm import Session
from app.api.models.predict import EmotionRecordSchema
from app.api.schemas.predict import EmotionRecordSchema

def create_emotion_record(db: Session, record: EmotionRecordSchema):
    db_obj = EmotionRecordSchema(**record.dict())
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_emotion_records_by_model(db: Session, modelo: str):
    return db.query(EmotionRecordSchema).filter(EmotionRecordSchema.modelo == modelo).all()