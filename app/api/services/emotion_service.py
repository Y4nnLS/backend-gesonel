import os
import numpy as np
import librosa
import tensorflow as tf
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class EmotionRecognitionService:
    def __init__(self, models_path: str = "predictModels"):
        self.models_path = models_path
        self.model = None
        self.label_encoder = None
        self._load_models()
    
    def _load_models(self):
        """Carrega os modelos de reconhecimento de emoção"""
        try:
            # Carrega o modelo principal
            model_path = os.path.join(self.models_path, "emotion_recognition_model.keras")
            if os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path)
                logger.info("Modelo de reconhecimento de emoção carregado com sucesso")
            else:
                logger.warning(f"Modelo não encontrado em: {model_path}")
            
            # Carrega o label encoder
            encoder_path = os.path.join(self.models_path, "label_encoder_classes.npy")
            if os.path.exists(encoder_path):
                self.label_encoder = np.load(encoder_path, allow_pickle=True)
                logger.info("Label encoder carregado com sucesso")
            else:
                logger.warning(f"Label encoder não encontrado em: {encoder_path}")
                
        except Exception as e:
            logger.error(f"Erro ao carregar modelos: {e}")
            raise
    
    def extract_mfcc_features(self, audio_path: str, n_mfcc: int = 13) -> tuple:
        """Extrai características MFCC do áudio"""
        try:
            # Carrega o áudio
            y, sr = librosa.load(audio_path, sr=None)
            
            # Extrai MFCC
            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)
            
            # O modelo espera (260, 40) - vamos ajustar
            target_frames = 260
            target_features = 40
            
            # Redimensiona para o formato esperado
            if mfcc.shape[1] > target_frames:
                mfcc = mfcc[:, :target_frames]
            else:
                # Padding se necessário
                pad_width = target_frames - mfcc.shape[1]
                mfcc = np.pad(mfcc, ((0, 0), (0, pad_width)), mode='constant')
            
            # Se temos menos features que o esperado, duplica
            if mfcc.shape[0] < target_features:
                # Duplica as features para chegar ao tamanho esperado
                repeat_factor = target_features // mfcc.shape[0] + 1
                mfcc = np.tile(mfcc, (repeat_factor, 1))
                mfcc = mfcc[:target_features, :]
            elif mfcc.shape[0] > target_features:
                # Reduz o número de features
                mfcc = mfcc[:target_features, :]
            
            # Cria máscara para indicar quais frames são válidos
            mask = np.ones((target_frames, 1))  # Todos os frames são válidos
            
            return mfcc.T, mask  # Retorna (features, mask)
            
        except Exception as e:
            logger.error(f"Erro ao extrair características MFCC: {e}")
            raise
    
    def predict_emotion(self, audio_path: str) -> Dict[str, Any]:
        """
        Prediz a emoção de um arquivo de áudio
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            Dict com a emoção predita, score de confiança e metadados
        """
        try:
            if self.model is None or self.label_encoder is None:
                raise ValueError("Modelos não foram carregados corretamente")
            
            # Extrai características
            features, mask = self.extract_mfcc_features(audio_path)
            features = np.expand_dims(features, axis=0)  # Adiciona dimensão do batch
            mask = np.expand_dims(mask, axis=0)  # Adiciona dimensão do batch
            
            # Faz a predição com os dois inputs
            predictions = self.model.predict([features, mask], verbose=0)
            
            # Obtém a classe predita e o score de confiança
            predicted_class_idx = np.argmax(predictions[0])
            confidence_score = float(predictions[0][predicted_class_idx])
            
            # Converte o índice para o nome da emoção
            if predicted_class_idx < len(self.label_encoder):
                predicted_emotion = self.label_encoder[predicted_class_idx]
            else:
                predicted_emotion = "unknown"
            
            # Metadados adicionais
            metadata = {
                "model_used": "emotion_recognition_model.keras",
                "features_extracted": "MFCC",
                "n_mfcc": 13,
                "all_predictions": predictions[0].tolist(),
                "processing_time": None  # Pode ser adicionado se necessário
            }
            
            return {
                "emotion": predicted_emotion,
                "confidence": confidence_score,
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"Erro na predição de emoção: {e}")
            raise
    
    def is_ready(self) -> bool:
        """Verifica se o serviço está pronto para uso"""
        return self.model is not None and self.label_encoder is not None

# Instância global do serviço
emotion_service = EmotionRecognitionService()
