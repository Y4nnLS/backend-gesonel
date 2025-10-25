"""
Exemplo de como usar a biblioteca externa no backend
"""
import os
import uuid
from typing import Dict, Any
from emotion_recognition_lib import EmotionPredictor, EmotionResult

class EmotionServiceWithLibrary:
    """
    Serviço de emoção usando a biblioteca externa
    """
    
    def __init__(self, models_path: str = None):
        self.predictor = EmotionPredictor(models_path)
    
    def is_ready(self) -> bool:
        """Verifica se o serviço está pronto"""
        return self.predictor.is_ready()
    
    def process_audio(self, audio_path: str) -> Dict[str, Any]:
        """
        Processa um arquivo de áudio usando a biblioteca
        
        Args:
            audio_path: Caminho para o arquivo de áudio
            
        Returns:
            Dict com os resultados do processamento
        """
        try:
            # Usa a biblioteca para fazer a predição
            result = self.predictor.predict(audio_path)
            
            # Converte para formato do banco de dados
            return {
                "emotion": result.emotion,
                "confidence": result.confidence,
                "metadata": result.metadata,
                "processing_time": result.processing_time,
                "error": result.error
            }
            
        except Exception as e:
            return {
                "emotion": "error",
                "confidence": 0.0,
                "metadata": {},
                "error": str(e)
            }

# Exemplo de uso no endpoint
def example_endpoint_usage():
    """
    Exemplo de como usar no endpoint de upload
    """
    # Inicializa o serviço
    emotion_service = EmotionServiceWithLibrary(
        models_path="C:/Users/FelipeFrancoPinheiro/Documents/modelosIA"
    )
    
    # Simula processamento
    audio_path = "example.wav"
    if os.path.exists(audio_path):
        result = emotion_service.process_audio(audio_path)
        print(f"Emoção: {result['emotion']}")
        print(f"Confiança: {result['confidence']:.3f}")
        print(f"Tempo: {result['processing_time']:.2f}s")

if __name__ == "__main__":
    example_endpoint_usage()
