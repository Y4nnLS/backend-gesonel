import uuid
import os
import hashlib
import librosa
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.api.core.db import get_db
from app.api.models.audio_file import AudioFile
from app.api.schemas.audio import AudioBasic
from app.api.services.emotion_service import emotion_service
from app.api.websocket import manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/upload", tags=["upload"])

# Diretório para salvar os arquivos de áudio
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def calculate_file_hash(file_path: str) -> str:
    """Calcula o hash SHA256 de um arquivo"""
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()

def get_audio_info(file_path: str) -> dict:
    """Extrai informações do arquivo de áudio"""
    try:
        y, sr = librosa.load(file_path, sr=None)
        duration = len(y) / sr
        return {
            "duration_s": duration,
            "sample_rate": sr,
            "channels": 1 if y.ndim == 1 else 2
        }
    except Exception as e:
        logger.error(f"Erro ao extrair informações do áudio: {e}")
        return {
            "duration_s": None,
            "sample_rate": None,
            "channels": None
        }

async def process_audio_background(audio_id: uuid.UUID, file_path: str, db: Session):
    """Processa o áudio em background para reconhecimento de emoção"""
    try:
        # Atualiza status para processando
        audio = db.get(AudioFile, audio_id)
        if audio:
            audio.processing_status = "processing"
            db.commit()
            
            # Envia update via WebSocket
            await manager.broadcast_audio_update(
                str(audio_id), 
                "processing", 
                {"rel_path": audio.rel_path}
            )
        
        # Verifica se o serviço está pronto
        if not emotion_service.is_ready():
            raise Exception("Serviço de reconhecimento de emoção não está pronto")
        
        # Faz a predição
        result = emotion_service.predict_emotion(file_path)
        
        # Atualiza o banco com os resultados
        audio = db.get(AudioFile, audio_id)
        if audio:
            audio.processing_status = "completed"
            audio.predicted_emotion = result["emotion"]
            audio.confidence_score = result["confidence"]
            audio.processing_metadata = result["metadata"]
            db.commit()
            
            # Envia update via WebSocket
            await manager.broadcast_audio_update(
                str(audio_id), 
                "completed", 
                {
                    "rel_path": audio.rel_path,
                    "predicted_emotion": result["emotion"],
                    "confidence_score": result["confidence"]
                }
            )
            
            logger.info(f"Processamento concluído para áudio {audio_id}: {result['emotion']} (confiança: {result['confidence']:.3f})")
        
    except Exception as e:
        logger.error(f"Erro no processamento do áudio {audio_id}: {e}")
        # Atualiza status para falha
        audio = db.get(AudioFile, audio_id)
        if audio:
            audio.processing_status = "failed"
            audio.processing_error = str(e)
            db.commit()
            
            # Envia update via WebSocket
            await manager.broadcast_audio_update(
                str(audio_id), 
                "failed", 
                {
                    "rel_path": audio.rel_path,
                    "error": str(e)
                }
            )

@router.post("/audio", response_model=AudioBasic, status_code=status.HTTP_201_CREATED)
async def upload_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload de arquivo de áudio para processamento de emoção
    """
    # Valida o tipo de arquivo
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400, 
            detail="Arquivo deve ser um áudio válido"
        )
    
    # Gera ID único para o arquivo
    audio_id = uuid.uuid4()
    
    # Define o caminho do arquivo
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.wav'
    file_path = os.path.join(UPLOAD_DIR, f"{audio_id}{file_extension}")
    
    try:
        # Salva o arquivo
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Calcula hash do arquivo
        file_hash = calculate_file_hash(file_path)
        
        # Verifica se já existe um arquivo com o mesmo hash
        existing = db.execute(
            select(AudioFile).where(AudioFile.sha256 == file_hash)
        ).scalar_one_or_none()
        
        if existing:
            # Remove o arquivo duplicado
            os.remove(file_path)
            raise HTTPException(
                status_code=409,
                detail="Arquivo com o mesmo conteúdo já existe"
            )
        
        # Extrai informações do áudio
        audio_info = get_audio_info(file_path)
        
        # Cria registro no banco
        audio_file = AudioFile(
            id=audio_id,
            rel_path=file_path,
            sha256=file_hash,
            format=file_extension[1:] if file_extension else None,
            duration_s=audio_info["duration_s"],
            sample_rate=audio_info["sample_rate"],
            channels=audio_info["channels"],
            processing_status="pending"
        )
        
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        
        # Agenda processamento em background
        background_tasks.add_task(process_audio_background, audio_id, file_path, db)
        
        logger.info(f"Arquivo {file.filename} enviado com sucesso. ID: {audio_id}")
        
        return audio_file
        
    except HTTPException:
        # Remove arquivo se houver erro HTTP
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        # Remove arquivo se houver erro geral
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Erro no upload do arquivo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno no upload: {str(e)}"
        )

@router.get("/status/{audio_id}")
async def get_processing_status(audio_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Verifica o status de processamento de um áudio
    """
    audio = db.get(AudioFile, audio_id)
    if not audio:
        raise HTTPException(status_code=404, detail="Áudio não encontrado")
    
    return {
        "id": audio.id,
        "processing_status": audio.processing_status,
        "predicted_emotion": audio.predicted_emotion,
        "confidence_score": audio.confidence_score,
        "processing_error": audio.processing_error,
        "created_at": audio.created_at,
        "updated_at": audio.updated_at
    }

@router.post("/file", response_model=AudioBasic, status_code=status.HTTP_201_CREATED)
async def upload_audio_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload de arquivo de áudio via multipart/form-data (compatível com frontend)
    """
    # Valida o tipo de arquivo
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(
            status_code=400, 
            detail="Arquivo deve ser um áudio válido"
        )
    
    # Gera ID único para o arquivo
    audio_id = uuid.uuid4()
    
    # Define o caminho do arquivo
    file_extension = os.path.splitext(file.filename)[1] if file.filename else '.wav'
    file_path = os.path.join(UPLOAD_DIR, f"{audio_id}{file_extension}")
    
    try:
        # Salva o arquivo
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Calcula hash do arquivo
        file_hash = calculate_file_hash(file_path)
        
        # Verifica se já existe um arquivo com o mesmo hash
        existing = db.execute(
            select(AudioFile).where(AudioFile.sha256 == file_hash)
        ).scalar_one_or_none()
        
        if existing:
            # Remove o arquivo duplicado
            os.remove(file_path)
            raise HTTPException(
                status_code=409,
                detail="Arquivo com o mesmo conteúdo já existe"
            )
        
        # Extrai informações do áudio
        audio_info = get_audio_info(file_path)
        
        # Cria registro no banco
        audio_file = AudioFile(
            id=audio_id,
            rel_path=file_path,
            sha256=file_hash,
            format=file_extension[1:] if file_extension else None,
            duration_s=audio_info["duration_s"],
            sample_rate=audio_info["sample_rate"],
            channels=audio_info["channels"],
            processing_status="pending"
        )
        
        db.add(audio_file)
        db.commit()
        db.refresh(audio_file)
        
        # Agenda processamento em background
        background_tasks.add_task(process_audio_background, audio_id, file_path, db)
        
        logger.info(f"Arquivo {file.filename} enviado com sucesso. ID: {audio_id}")
        
        return audio_file
        
    except HTTPException:
        # Remove arquivo se houver erro HTTP
        if os.path.exists(file_path):
            os.remove(file_path)
        raise
    except Exception as e:
        # Remove arquivo se houver erro geral
        if os.path.exists(file_path):
            os.remove(file_path)
        logger.error(f"Erro no upload do arquivo: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro interno no upload: {str(e)}"
        )
