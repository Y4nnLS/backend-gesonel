import uuid
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.core.db import get_db
from app.api.schemas.audio import AudioBasic, AudioCreate, AudioUpdate, AudioListResponse

from app.api.crud.audio_file import (
    create_audio_file,
    get_audio_file,
    list_audio_files,
    update_audio_file,
    delete_audio_file
)

router = APIRouter(prefix="/v1/audios", tags=["audios"])

UPLOAD_DIR = "db-stack/audios/uploaded"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- READ ----------

@router.get("", response_model=AudioListResponse)
def list_audios(
    limit: Optional[int] = Query(None, ge=1, le=500),   
    offset: Optional[int] = Query(None, ge=0),
    dataset: Optional[str] = None,
    label: Optional[str] = Query(None, alias="emotion_label"),
    db: Session = Depends(get_db),
):
    # Monta filtros
    items = list_audio_files(db)
    # Filtros e paginação podem ser implementados dentro da função list_audio_files se desejar
    # Aqui está um filtro simples em Python, mas o ideal é filtrar no SQL
    if dataset:
        items = [audio for audio in items if audio.dataset == dataset]
    if label:
        items = [audio for audio in items if audio.emotion_label == label]
    totalRecords = len(items)
    if offset is not None:
        items = items[offset:]
    if limit is not None:
        items = items[:limit]
    return {"items": items, "totalRecords": totalRecords}

@router.get("/{audio_id}", response_model=AudioBasic)
def get_audio_by_id(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = get_audio_file(db, str(audio_id))
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    return obj

# ---------- CREATE ----------

@router.post(
    "/postAudio",
    response_model=AudioBasic,
    status_code=status.HTTP_201_CREATED,
    operation_id="uploadAudio",
)
async def upload_audio(file: UploadFile = File(...), db: Session = Depends(get_db)):
    file_location = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_location, "wb") as buffer:
        buffer.write(await file.read())
    # Crie o objeto AudioCreate com os metadados e caminho relativo
    audio_data = AudioCreate(
        filename=file.filename,
        rel_path=file_location,
        duration_s=0.0  # Preencha conforme necessário
    )
    try:
        obj = create_audio_file(db, audio_data)
    except Exception as e:
        raise HTTPException(status_code=409, detail="Conflito: sha256 já existe") from e
    return obj

# ---------- DOWNLOAD ----------
@router.get("/download/{audio_id}")
def download_audio_file(audio_id: str, db: Session = Depends(get_db)):
    audio_obj = get_audio_file(db, audio_id)
    if not audio_obj:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    file_path = audio_obj.rel_path
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Arquivo físico não encontrado")
    return FileResponse(path=file_path, filename=audio_obj.filename, media_type="audio/wav")

# ---------- UPDATE ----------

@router.put("/{audio_id}", response_model=AudioBasic)
def update_audio(audio_id: uuid.UUID, payload: AudioUpdate, db: Session = Depends(get_db)):
    obj = update_audio_file(db, str(audio_id), payload)
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    return obj

# ---------- DELETE ----------

@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = delete_audio_file(db, str(audio_id))
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    return None
