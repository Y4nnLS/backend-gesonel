"""
Modelos de dados para a biblioteca de reconhecimento de emoções
"""
from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum

class ProcessingStatus(Enum):
    """Status do processamento"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class EmotionResult:
    """Resultado da predição de emoção"""
    emotion: str
    confidence: float
    metadata: Dict[str, Any]
    processing_time: Optional[float] = None
    error: Optional[str] = None

@dataclass
class AudioInfo:
    """Informações do arquivo de áudio"""
    duration: float
    sample_rate: int
    channels: int
    format: str
