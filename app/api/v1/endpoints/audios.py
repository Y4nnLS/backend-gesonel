import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.api.core.db import get_db
from app.api.models.audio_file import AudioFile
from app.api.schemas.audio import AudioBasic, AudioCreate, AudioUpdate

router = APIRouter(prefix="/v1/audios", tags=["audios"])

# ---------- READ ----------

@router.get("", response_model=list[AudioBasic])
def list_audios(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    dataset: str | None = None,
    label: str | None = Query(None, alias="emotion_label"),
    db: Session = Depends(get_db),
):
    stmt = select(AudioFile)
    if dataset:
        stmt = stmt.where(AudioFile.dataset == dataset)
    if label:
        stmt = stmt.where(AudioFile.emotion_label == label)
    stmt = stmt.offset(offset).limit(limit)
    rows = db.execute(stmt).scalars().all()
    return rows


@router.get("/{audio_id}", response_model=AudioBasic)
def get_audio_by_id(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    stmt = select(AudioFile).where(AudioFile.id == audio_id)
    obj = db.execute(stmt).scalar_one_or_none()
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    return obj

# ---------- CREATE ----------

# ... imports e router iguais ...

# ---------- UPLOAD (antes era create) ----------
@router.post(
    "/upload",
    response_model=AudioBasic,
    status_code=status.HTTP_201_CREATED,
    operation_id="uploadAudio",  # nome exato no OpenAPI
)
def upload_audio(payload: AudioCreate, db: Session = Depends(get_db)):
    obj = AudioFile(
        rel_path=payload.rel_path,
        sha256=payload.sha256,
        format=payload.format,
        duration_s=payload.duration_s,
        sample_rate=payload.sample_rate,
        channels=payload.channels,
        dataset=payload.dataset,
        speaker_id=payload.speaker_id,
        emotion_label=payload.emotion_label,
        split=payload.split,
        augment_pipeline=payload.augment_pipeline,
    )
    db.add(obj)
    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito: sha256 já existe") from e
    db.refresh(obj)
    return obj


# ---------- UPDATE (PUT: substitui campos do recurso) ----------

@router.put("/{audio_id}", response_model=AudioBasic)
def update_audio(audio_id: uuid.UUID, payload: AudioUpdate, db: Session = Depends(get_db)):
    obj = db.get(AudioFile, audio_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")

    obj.rel_path = payload.rel_path
    obj.sha256 = payload.sha256
    obj.format = payload.format
    obj.duration_s = payload.duration_s
    obj.sample_rate = payload.sample_rate
    obj.channels = payload.channels
    obj.dataset = payload.dataset
    obj.speaker_id = payload.speaker_id
    obj.emotion_label = payload.emotion_label
    obj.split = payload.split
    obj.augment_pipeline = payload.augment_pipeline

    try:
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=409, detail="Conflito: sha256 já existe") from e
    db.refresh(obj)
    return obj

# ---------- DELETE ----------

@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = db.get(AudioFile, audio_id)
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    db.delete(obj)
    db.commit()
    return None
