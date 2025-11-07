import uuid
import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path
import mimetypes
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

UPLOAD_DIR = "D:/audios/uploaded"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ---------- READ ----------

@router.get("", response_model=AudioListResponse)
def list_audios(
    limit: Optional[int] = Query(None, ge=1, le=500),   
    offset: Optional[int] = Query(None, ge=0),
    dataset: Optional[str] = None,
    label: Optional[str] = Query(None, alias="emotion_label"),
    pending: Optional[bool] = Query(
        None,
        description="True: somente pending; False: tudo que não é pending; None: todos",
    ),
    db: Session = Depends(get_db),
):
    items = list_audio_files(db)

    if dataset:
        items = [a for a in items if a.dataset == dataset]
    if label:
        items = [a for a in items if a.emotion_label == label]

    if pending is True:
        items = [a for a in items if (a.processing_status or "").lower() == "pending"]
    elif pending is False:
        items = [a for a in items if (a.processing_status or "").lower() != "pending"]

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
    # try:
    obj = create_audio_file(db, audio_data)
    # except Exception as e:
    #     raise HTTPException(status_code=409, detail="Conflito: sha256 já existe") from e
    return obj

# ---------- DOWNLOAD ----------
AUDIO_ROOT = Path("D:/audios").resolve()

def safe_join(base: Path, rel_path: str) -> Path:
    rel_norm = (rel_path or "").replace("\\", "/")
    p = (base / rel_norm).resolve()
    if base not in p.parents and p != base:
        raise HTTPException(status_code=400, detail="Caminho inválido")
    return p

@router.get("/download/{audio_id}")
def download_audio_file(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    audio_obj = get_audio_file(db, str(audio_id))
    if not audio_obj:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")

    file_path = safe_join(AUDIO_ROOT, audio_obj.rel_path or "")
    if not file_path.exists():
        # tenta adicionar .wav caso o rel_path esteja sem extensão
        cand = file_path.with_suffix(".wav")
        if cand.exists():
            file_path = cand
        else:
            raise HTTPException(status_code=404, detail="Arquivo físico não encontrado")

    # Nome de download: basename do rel_path (garante .wav)
    download_name = Path(audio_obj.rel_path).name or str(audio_id)
    if not download_name.lower().endswith(".wav"):
        download_name += ".wav"

    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=download_name,
    )
# ---------- UPDATE ----------

# @router.put("/{audio_id}", response_model=AudioBasic)
# def update_audio(audio_id: uuid.UUID, payload: AudioUpdate, db: Session = Depends(get_db)):
#     obj = update_audio_file(db, str(audio_id), payload)
#     if obj is None:
#         raise HTTPException(status_code=404, detail="Áudio não encontrado")
#     return obj

# ---------- DELETE ----------

@router.delete("/{audio_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_audio(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    obj = delete_audio_file(db, str(audio_id))
    if obj is None:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    return None
