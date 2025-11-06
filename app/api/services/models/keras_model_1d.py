from __future__ import annotations
import os
from typing import Dict, List, Optional

import numpy as np
import librosa
import tensorflow as tf

from .base import BaseEmotionModel

TARGET_FRAMES = 260
TARGET_FEATURES = 40
N_MFCC = 40
SAMPLE_RATE = 22050
N_MFCC = 40
MAX_PAD_LEN = 260

class KerasEmotionModel(BaseEmotionModel):
    """
    Wrapper do arquivo .keras (mesma lógica de pré-processo do EmotionRecognitionService)
    """
    name = "keras_emotion"
    version = "1.0.0"

    def __init__(self, model_path: Optional[str] = None, labels_path: Optional[str] = None, **kw):
        super().__init__(**kw)
        base = os.getenv("PREDICT_MODELS_PATH", "predictModels")
        self.model_path = model_path or os.getenv("keras_model_1d_PATH", os.path.join(base, "best_model_mfcc.keras"))
        self.labels_path = labels_path or os.path.join(base, "label_encoder_classes.npy")
        self._model: Optional[tf.keras.Model] = None
        self._labels: Optional[List[str]] = None
        os.environ.setdefault("TF_FORCE_GPU_ALLOW_GROWTH", "true")

    def load(self) -> None:
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(f"Arquivo Keras não encontrado: {self.model_path}")
        self._model = tf.keras.models.load_model(self.model_path, compile=False)
        if os.path.exists(self.labels_path):
            enc = np.load(self.labels_path, allow_pickle=True)
            self._labels = [str(x) for x in enc.tolist()]
        else:
            self._labels = None
        self._loaded = True

    def _extract(self, audio_path: str) -> tuple[np.ndarray, np.ndarray]:
        print("CUUUUUUUUUUUUUUUUUUUUUUU")
        try:
            audio, _ = librosa.load(audio_path, sr=SAMPLE_RATE, mono=True)
            mfccs = librosa.feature.mfcc(y=audio, sr=SAMPLE_RATE, n_mfcc=N_MFCC)
            
            # Padding/Trimming
            if mfccs.shape[1] > MAX_PAD_LEN:
                mfccs = mfccs[:, :MAX_PAD_LEN]
            else:
                pad_width = MAX_PAD_LEN - mfccs.shape[1]
                mfccs = np.pad(mfccs, pad_width=((0, 0), (0, pad_width)), mode='constant')
            
            # Reformata para o shape do modelo
            mfccs = np.transpose(mfccs)  # (MAX_PAD_LEN, N_MFCC)
            mfccs = np.expand_dims(mfccs, axis=0)  # (1, MAX_PAD_LEN, N_MFCC)
            print("MFCCs extraídos com sucesso")
            print(mfccs.shape)
            return mfccs, True
        
        except Exception as e:
            print(f"Erro ao processar {audio_path}: {e}")
            return None, False
        # y, sr = librosa.load(audio_path, sr=None, mono=True)
        # mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=N_MFCC).T  # (T0, n_mfcc)
        # T0 = mfcc.shape[0]
        # T_use = min(T0, TARGET_FRAMES)

        # feats = np.zeros((TARGET_FRAMES, TARGET_FEATURES), dtype=np.float32)
        # feats[:T_use, :min(N_MFCC, TARGET_FEATURES)] = mfcc[:T_use, :min(N_MFCC, TARGET_FEATURES)]
        # if N_MFCC < TARGET_FEATURES:
        #     reps = int(np.ceil(TARGET_FEATURES / N_MFCC))
        #     tiled = np.tile(mfcc[:T_use, :N_MFCC], (1, reps))[:, :TARGET_FEATURES]
        #     feats[:T_use, :] = tiled

        # mask = np.zeros((TARGET_FRAMES, 1), dtype=np.float32)
        # mask[:T_use, 0] = 1.0

        # if T_use > 0:
        #     valid = feats[:T_use, :]
        #     mean = valid.mean(axis=0, keepdims=True)
        #     std = valid.std(axis=0, keepdims=True) + 1e-8
        #     feats[:T_use, :] = (valid - mean) / std

        # return feats.astype(np.float32), mask.astype(np.float32)

    def predict(self, file_path: str) -> Dict[str, float]:
        self.ensure_loaded()
        # Configurações de caminhos
        MODELO_CAMINHO = "predictModels\\best_model_mfcc.keras"
        LABEL_ENCODER_CAMINHO = "predictModels\\label_encoder_classes.npy"  # 👈 Arquivo .npy
        
        # Verificar se arquivos existem
        if not os.path.exists(MODELO_CAMINHO):
            print(f"❌ Modelo não encontrado: {MODELO_CAMINHO}")
            return
        
        if not os.path.exists(LABEL_ENCODER_CAMINHO):
            print(f"❌ LabelEncoder (.npy) não encontrado: {LABEL_ENCODER_CAMINHO}")
            return
        
        # Carregar modelo
        print("🚀 Carregando modelo...")
        modelo = tf.keras.models.load_model(MODELO_CAMINHO)
        
        # Carregar LabelEncoder a partir do .npy
        print("📁 Carregando classes do arquivo .npy...")
        classes = np.load(LABEL_ENCODER_CAMINHO, allow_pickle=True)
        
        print(f"🎭 Emoções reconhecidas: {list(classes)}")
        
        # Loop de inferência
        print("\n" + "="*60)
        caminho_audio = file_path
        
        # Processar áudio
        audio_processado, sucesso = self._extract(caminho_audio)
        
        # Fazer predição
        predictions = modelo.predict(audio_processado, verbose=0)
        classe_idx = np.argmax(predictions[0])
        confianca = predictions[0][classe_idx] * 100
        emocao = classes[classe_idx]
        
        # Mostrar resultados
        print(f"\n📊 RESULTADO:")
        print(f"Arquivo: {os.path.basename(caminho_audio)}")
        print(f"🎭 Emoção detectada: {emocao.upper()}")
        print(f"✅ Confiança: {confianca:.2f}%")
        
        print(f"\n📈 Probabilidades detalhadas:")
        for idx, classe in enumerate(classes):
            prob = predictions[0][idx] * 100
            bar = "█" * int(prob / 5)  # Barra visual
            marcador = "👈" if idx == classe_idx else ""
            print(f"  {classe:10}: {prob:5.2f}% {bar} {marcador}")
        # --- retorno para o backend salvar no banco ---
        # (use probabilidades 0..1; os *prints* usam % só para exibição)
        scores = {str(classes[i]): float(predictions[0][i]) for i in range(len(classes))}
        return scores

        # x, m = self._extract(file_path)
        # x = x[None, ...]  # (1,T,F)
        # m = m[None, ...]  # (1,T,1)
        # preds = self._model.predict([x, m], verbose=0)
        # preds = np.asarray(preds, dtype=np.float32)[0]
        # s = float(preds.sum())
        # if not np.isfinite(s) or abs(s - 1.0) > 1e-3:
        #     e = np.exp(preds - preds.max())
        #     preds = e / e.sum()

        # labels = self._labels or [str(i) for i in range(len(preds))]
        # if len(labels) != len(preds):
        #     labels = [str(i) for i in range(len(preds))]
        # return {lbl: float(p) for lbl, p in zip(labels, preds)}
