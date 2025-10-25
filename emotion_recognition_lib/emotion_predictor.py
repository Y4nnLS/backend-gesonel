"""
Classe principal para predição de emoções
"""
import os
import time
import logging
from typing import Optional, Dict, Any
import numpy as np
import librosa
import tensorflow as tf

from .models import EmotionResult, AudioInfo, ProcessingStatus

logger = logging.getLogger(__name__)

class EmotionPredictor:
    """
    Classe para predição de emoções em arquivos de áudio
    """
    
    def __init__(self, models_path: str = None):
        """
        Inicializa o preditor de emoções
        
        Args:
            models_path: Caminho para os modelos (opcional)
        """
        self.models_path = models_path or os.getenv("EMOTION_MODELS_PATH", "./models")
        self.model = None
        self.label_encoder = None
        self._load_models()
    
    def _load_models(self):
        """Carrega os modelos necessários"""
        try:
            # Carrega o modelo principal
            model_path = os.path.join(self.models_path, "emotion_recognition_model.keras")
            if os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path)
                logger.info("Modelo carregado com sucesso")
            else:
                logger.warning(f"Modelo não encontrado: {model_path}")
            
            # Carrega o label encoder
            encoder_path = os.path.join(self.models_path, "label_encoder_classes.npy")
            if os.path.exists(encoder_path):
                self.label_encoder = np.load(encoder_path, allow_pickle=True)
                logger.info("Label encoder carregado com sucesso")
            else:
                logger.warning(f"Label encoder não encontrado: {encoder_path}")
                
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Verifica se o preditor está pronto para uso"""
        return self.model is not None and self.label_encoder is not None
    
    def get_audio_info(self, audio_path: str) -> AudioInfo:
        """
        Extrai informações do arquivo de áudio
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            AudioInfo com as informações do áudio
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            duration = len(y) / sr
            channels = 1 if y.ndim == 1 else 2
            format_name = os.path.splitext(audio_path)[1][1:].lower()
            
            return AudioInfo(
                duration=duration,
                sample_rate=sr,
                channels=channels,
                format=format_name
            )
        except Exception as e:
            logger.error(f"Erro ao extrair informações do áudio: {e}")
            raise
    
    def extract_features(self, audio_path: str, n_mfcc: int = 13) -> np.ndarray:
        """
        Extrai características MFCC do áudio
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            n_mfcc: Número de coeficientes MFCC
            
        Returns:
            Array com as características extraídas
        """
        try:
            y, sr = librosa.load(audio_path, sr=None)
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
            
            # Padroniza o tamanho
            target_frames = 100
            if mfcc.shape[1] > target_frames:
                mfcc = mfcc[:, :target_frames]
            else:
                pad_width = target_frames - mfcc.shape[1]
                mfcc = np.pad(mfcc, ((0, 0), (0, pad_width)), mode='constant')
            
            return mfcc.T
        except Exception as e:
            logger.error(f"Erro ao extrair características: {e}")
            raise
    
    def predict(self, audio_path: str) -> EmotionResult:
        """
        Prediz a emoção de um arquivo de áudio
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            EmotionResult com a predição
        """
        start_time = time.time()
        
        try:
            if not self.is_ready():
                raise ValueError("Modelos não carregados")
            
            # Extrai características
            features = self.extract_features(audio_path)
            features = np.expand_dims(features, axis=0)
            
            # Faz a predição
            predictions = self.model.predict(features, verbose=0)
            
            # Processa resultados
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            
            # Converte para nome da emoção
            if predicted_class_idx < len(self.label_encoder):
                emotion = self.label_encoder[predicted_class_idx]
            else:
                emotion = "unknown"
            
            processing_time = time.time() - start_time
            
            # Metadados
            metadata = {
                "model_used": "emotion_recognition_model.keras",
                "features": "MFCC",
                "n_mfcc": 13,
                "all_predictions": predictions[0].tolist(),
                "processing_time": processing_time
            }
            
            return EmotionResult(
                emotion=emotion,
                confidence=confidence,
                metadata=metadata,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return EmotionResult(
                emotion="error",
                confidence=0.0,
                metadata={},
                error=str(e)
            )
    
    def predict_batch(self, audio_paths: list) -> list[EmotionResult]:
        """
        Prediz emoções para múltiplos arquivos
        
        Args:
            audio_paths: Lista de caminhos para arquivos de áudio
            
        Returns:
            Lista de EmotionResult
        """
        results = []
        for audio_path in audio_paths:
            try:
                result = self.predict(audio_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Erro no processamento de {audio_path}: {e}")
                results.append(EmotionResult(
                    emotion="error",
                    confidence=0.0,
                    metadata={},
                    error=str(e)
                ))
        return results
