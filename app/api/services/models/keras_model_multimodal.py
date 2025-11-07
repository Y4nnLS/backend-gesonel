from __future__ import annotations
import os
from typing import Dict, List, Optional, Tuple

import numpy as np
import tensorflow as tf
from tensorflow.keras.applications.efficientnet_v2 import preprocess_input as eff_pre

from .base import BaseEmotionModel
# usa exatamente o teu extrator, sem salvar imagens
from ..extract_lib import extract_features_np

# ===== Configs (alinhar ao treino) =====
SAMPLE_RATE   = int(os.getenv("MULTIMODAL_SAMPLE_RATE", "22050"))
N_FFT         = int(os.getenv("MULTIMODAL_N_FFT", "2048"))
HOP_LENGTH    = int(os.getenv("MULTIMODAL_HOP", "512"))
N_MFCC_DD     = int(os.getenv("MULTIMODAL_N_MFCC_DD", "13"))
IMG_H         = int(os.getenv("MULTIMODAL_IMG_H", "300"))
IMG_W         = int(os.getenv("MULTIMODAL_IMG_W", "300"))
FIXED_1D_LEN  = int(os.getenv("MULTIMODAL_FIXED_1D", "512"))   # ZCR(512)+RMS(512)=1024

def _resize_and_preprocess_rgb(uint8_rgb: np.ndarray) -> np.ndarray:
    """Redimensiona e aplica preprocess EXATAMENTE como no classify.py (EfficientNetV2)."""
    x = tf.convert_to_tensor(uint8_rgb, dtype=tf.uint8)
    x = tf.image.resize(x, (IMG_H, IMG_W), method="bilinear")
    x = tf.cast(x, tf.float32)  # [0..255]
    x = eff_pre(x)              # === igual ao classify.py ===
    return x.numpy()

def _pad_or_trim_1d(x: np.ndarray, L: int = FIXED_1D_LEN) -> np.ndarray:
    v = np.asarray(x, dtype=np.float32).ravel()
    if v.size >= L:
        return v[:L]
    out = np.zeros((L,), dtype=np.float32)
    out[:v.size] = v
    return out

class KerasMultimodalEmotionModel(BaseEmotionModel):
    """Multimodal (dd_mfcc + chroma + zcr/rms) — INFERÊNCIA APENAS."""
    name = "keras_multimodal"
    version = "1.0.0"

    def __init__(self, model_path: Optional[str] = None, labels_path: Optional[str] = None, **kw):
        super().__init__(**kw)
        base = os.getenv("PREDICT_MODELS_PATH", "predictModels")
        self.model_path  = model_path  or os.getenv(
            "keras_model_multimodal_PATH",
            os.path.join(base, "best_model_finetuned.keras")
        )
        self.labels_path = labels_path or os.path.join(base, "label_encoder_classes.npy")
        self._model: Optional[tf.keras.Model] = None
        self._labels: Optional[List[str]] = None
        os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")

    def load(self) -> None:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Arquivo Keras não encontrado: {self.model_path}")

        # importa o stub e passa no custom_objects
        from app.api.services.models.spec_augment_stub import SpecAugment

        self._model = tf.keras.models.load_model(
            self.model_path,
            compile=False,
            custom_objects={
                # mapeia pelo nome registrado
                "SpecAugment": SpecAugment,
            },
            safe_mode=False,  # importante p/ grafos com objetos não-registrados
        )

        if os.path.exists(self.labels_path):
            enc = np.load(self.labels_path, allow_pickle=True)
            self._labels = [str(x) for x in enc.tolist()]
        else:
            self._labels = None

        self._loaded = True


    def _extract_inputs(self, audio_path: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        # usa teu extractor em memória (idêntico ao training kernel visual)
        dd_mfcc_img_rgb, chroma_img_rgb, zcr, rms = extract_features_np(
            audio_path,
            target_sr=SAMPLE_RATE,
            n_fft=N_FFT,
            hop=HOP_LENGTH,
            n_mfcc_dd=N_MFCC_DD,
        )
        mfcc_img   = _resize_and_preprocess_rgb(dd_mfcc_img_rgb)
        chroma_img = _resize_and_preprocess_rgb(chroma_img_rgb)

        zcr_fix = _pad_or_trim_1d(zcr, FIXED_1D_LEN)
        rms_fix = _pad_or_trim_1d(rms, FIXED_1D_LEN)
        numerical = np.concatenate([zcr_fix, rms_fix], axis=0).astype("float32")  # (1024,)

        return (
            np.expand_dims(mfcc_img, axis=0),       # (1,H,W,3)
            np.expand_dims(chroma_img, axis=0),     # (1,H,W,3)
            np.expand_dims(numerical, axis=0),      # (1,1024)
        )

    def _print_prediction_summary(self, file_path: str, labels: List[str], probs: np.ndarray) -> None:
        base = os.path.basename(file_path)
        idx = int(np.argmax(probs))
        top_label = labels[idx] if idx < len(labels) else str(idx)
        conf_pct = float(probs[idx]) * 100.0

        print("================================ MULTIMODAL ================================")
        print("📊 RESULTADO:")
        print(f"Arquivo: {base}")
        print(f"🎭 Emoção detectada: {top_label.upper()}")
        print(f"✅ Confiança: {conf_pct:.2f}%\n")

        print("📈 Probabilidades detalhadas:")
        for i, lbl in enumerate(labels):
            p = float(probs[i]) * 100.0
            bar = "█" * int(p / 5.0)
            marker = " 👈" if i == idx else ""
            print(f"  {lbl.lower():10}: {p:6.2f}% {bar}{marker}")

    def predict(self, file_path: str) -> Dict[str, float]:
        self.ensure_loaded()
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Áudio não encontrado: {file_path}")

        mfcc_img, chroma_img, numerical = self._extract_inputs(file_path)

        try:
            probs = self._model.predict(
                {
                    "mfcc_input": mfcc_img,
                    "chroma_input": chroma_img,
                    "numerical_input": numerical,
                },
                verbose=0
            )[0]
        except Exception as e:
            raise RuntimeError(f"Falha na inferência: {e}")

        probs = np.asarray(probs, dtype=np.float32)
        s = float(probs.sum())
        if not np.isfinite(s) or abs(s - 1.0) > 1e-3:
            e = np.exp(probs - probs.max())
            probs = e / e.sum()

        labels = self._labels or [str(i) for i in range(len(probs))]
        if len(labels) != len(probs):
            labels = [str(i) for i in range(len(probs))]

        self._print_prediction_summary(file_path, labels, probs)
        return {lbl: float(p) for lbl, p in zip(labels, probs)}
