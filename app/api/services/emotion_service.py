import os
import time
import numpy as np
import librosa
import tensorflow as tf
from typing import Dict, Any, Optional, Tuple, List
import logging

logger = logging.getLogger(__name__)

def _to_float32(x: np.ndarray) -> np.ndarray:
    return np.asarray(x, dtype=np.float32, order="C")

class EmotionRecognitionService:
    """
    Serviço Keras (.keras) com dois inputs: [features(T,F), mask(T,1)].
    - features = MFCC (T x F) com padding
    - mask[t,0] = 1 para frames reais, 0 para padding
    """
    def __init__(self, models_path: Optional[str] = None):
        self.models_path = models_path or os.getenv("PREDICT_MODELS_PATH", "predictModels")
        self.model: Optional[tf.keras.Model] = None
        self.label_encoder: Optional[List[str]] = None
        os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")
        self._load_models()

    def _load_models(self) -> None:
        model_path = os.path.join(self.models_path, "emotion_recognition_model.keras")
        encoder_path = os.path.join(self.models_path, "label_encoder_classes.npy")
        try:
            if os.path.exists(model_path):
                self.model = tf.keras.models.load_model(model_path, compile=False)
                logger.info(f"[Emotion] Modelo carregado: {model_path}")
            else:
                logger.warning(f"[Emotion] Modelo NÃO encontrado: {model_path}")

            if os.path.exists(encoder_path):
                enc = np.load(encoder_path, allow_pickle=True)
                self.label_encoder = [str(x) for x in enc.tolist()]
                logger.info(f"[Emotion] Labels carregados: {len(self.label_encoder)} classes")
            else:
                logger.warning(f"[Emotion] Labels NÃO encontrados: {encoder_path}")
        except Exception:
            logger.exception("[Emotion] Falha ao carregar artefatos")
            raise

    def is_ready(self) -> bool:
        return self.model is not None and self.label_encoder is not None

    def extract_mfcc_features(
        self,
        audio_path: str,
        n_mfcc: int = 13,
        target_frames: int = 260,
        target_features: int = 40,
        normalize: bool = True,
    ) -> Tuple[np.ndarray, np.ndarray, int]:
        """
        Retorna (features[T,F], mask[T,1], sr) em float32.
        """
        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Áudio não encontrado: {audio_path}")

            y, sr = librosa.load(audio_path, sr=None, mono=True)

            mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=n_mfcc)  # (n_mfcc, T0)
            mfcc = mfcc.T  # (T0, n_mfcc)

            T0 = mfcc.shape[0]
            T_use = min(T0, target_frames)

            feats = np.zeros((target_frames, target_features), dtype=np.float32)
            feats[:T_use, :min(n_mfcc, target_features)] = mfcc[:T_use, :min(n_mfcc, target_features)]

            if n_mfcc < target_features:
                reps = int(np.ceil(target_features / n_mfcc))
                tiled = np.tile(mfcc[:T_use, :n_mfcc], (1, reps))[:, :target_features]
                feats[:T_use, :] = tiled

            mask = np.zeros((target_frames, 1), dtype=np.float32)
            mask[:T_use, 0] = 1.0

            if normalize and T_use > 0:
                valid = feats[:T_use, :]
                mean = valid.mean(axis=0, keepdims=True)
                std = valid.std(axis=0, keepdims=True) + 1e-8
                feats[:T_use, :] = (valid - mean) / std

            return _to_float32(feats), _to_float32(mask), sr

        except Exception:
            logger.exception("[Emotion] Erro ao extrair MFCC")
            raise

    def predict_emotion(self, audio_path: str) -> Dict[str, Any]:
        """
        Saída:
        {
          "emotion": <str>,
          "confidence": <float>,
          "scores": {label: prob, ...},
          "metadata": {...}
        }
        """
        try:
            if not self.is_ready():
                raise ValueError("Serviço não pronto (modelo/labels ausentes)")

            t0 = time.perf_counter()
            feats, mask, sr = self.extract_mfcc_features(audio_path)

            x_feats = feats[None, ...]  # (1,T,F)
            x_mask = mask[None, ...]    # (1,T,1)

            preds = self.model.predict([x_feats, x_mask], verbose=0)
            preds = np.asarray(preds, dtype=np.float32)

            if preds.ndim != 2 or preds.shape[0] != 1:
                raise ValueError(f"Saída inesperada do modelo: shape={preds.shape}")

            p = preds[0]
            s = float(p.sum())
            if not np.isfinite(s) or abs(s - 1.0) > 1e-3:
                e = np.exp(p - p.max())
                p = e / e.sum()

            labels = self.label_encoder or [str(i) for i in range(len(p))]
            if len(labels) != len(p):
                logger.warning(f"[Emotion] nº labels ({len(labels)}) != nº logits ({len(p)})")
                labels = [str(i) for i in range(len(p))]

            scores = {lbl: float(prob) for lbl, prob in zip(labels, p)}
            top_idx = int(np.argmax(p))
            top_label = labels[top_idx]
            latency_ms = (time.perf_counter() - t0) * 1000.0

            return {
                "emotion": top_label,
                "confidence": float(p[top_idx]),
                "scores": scores,
                "metadata": {
                    "model_used": "emotion_recognition_model.keras",
                    "features_extracted": "MFCC",
                    "n_mfcc": int(feats.shape[1]),
                    "sample_rate": sr,
                    "processing_time_ms": latency_ms,
                    "input_shapes": {"features": x_feats.shape, "mask": x_mask.shape},
                },
            }

        except Exception:
            logger.exception("[Emotion] Erro na predição")
            raise

# singleton
emotion_service = EmotionRecognitionService()
