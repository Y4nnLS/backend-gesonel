"""
Interface de linha de comando para a biblioteca
"""
import argparse
import sys
import json
from pathlib import Path

from .emotion_predictor import EmotionPredictor
from .models import ProcessingStatus

def main():
    """Função principal da CLI"""
    parser = argparse.ArgumentParser(
        description="Reconhecimento de emoções em áudio"
    )
    parser.add_argument(
        "audio_file",
        help="Caminho para o arquivo de áudio"
    )
    parser.add_argument(
        "--models-path",
        help="Caminho para os modelos",
        default="./models"
    )
    parser.add_argument(
        "--output",
        help="Arquivo de saída (JSON)",
        default=None
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Saída verbosa"
    )
    
    args = parser.parse_args()
    
    try:
        # Inicializa o preditor
        predictor = EmotionPredictor(models_path=args.models_path)
        
        if not predictor.is_ready():
            print("❌ Modelos não carregados corretamente", file=sys.stderr)
            sys.exit(1)
        
        # Faz a predição
        result = predictor.predict(args.audio_file)
        
        # Prepara saída
        output = {
            "audio_file": args.audio_file,
            "emotion": result.emotion,
            "confidence": result.confidence,
            "processing_time": result.processing_time,
            "metadata": result.metadata
        }
        
        if result.error:
            output["error"] = result.error
        
        # Salva ou exibe resultado
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"✅ Resultado salvo em: {args.output}")
        else:
            print(json.dumps(output, indent=2))
            
    except Exception as e:
        print(f"❌ Erro: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
