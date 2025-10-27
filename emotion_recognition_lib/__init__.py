"""
Biblioteca externa para reconhecimento de emoções em áudio
"""
from .emotion_predictor import EmotionPredictor
from .models import EmotionResult, ProcessingStatus

__version__ = "1.0.0"
__all__ = ["EmotionPredictor", "EmotionResult", "ProcessingStatus"]
