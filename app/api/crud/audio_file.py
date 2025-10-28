from sqlalchemy.orm import Session
from app.api.models.audio_file import AudioFile
from app.api.schemas.audio import AudioFileSchema
import uuid

def create_audio_file(db: Session, audio: AudioFileSchema):
    db_obj = AudioFile(**audio.dict())
    if getattr(db_obj, "id", None) is None:
        db_obj.id = uuid.uuid4()
    db.add(db_obj)
    db.commit()
    db.refresh(db_obj)
    return db_obj

def get_audio_file(db: Session, audio_id: str):
    return db.query(AudioFile).filter(AudioFile.id == audio_id).first()

def list_audio_files(db: Session):
    return db.query(AudioFile).all()

def update_audio_file(db: Session, audio_id: str, audio: AudioFileSchema):
    db_obj = get_audio_file(db, audio_id)
    if db_obj:
        for key, value in audio.dict().items():
            setattr(db_obj, key, value)
        db.commit()
        db.refresh(db_obj)
    return db_obj

def delete_audio_file(db: Session, audio_id: str):
    db_obj = get_audio_file(db, audio_id)
    if db_obj:
        db.delete(db_obj)
        db.commit()
    return db_obj