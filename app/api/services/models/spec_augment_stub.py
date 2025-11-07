# stub identidade para desserializar modelos que possuem SpecAugment no grafo
from __future__ import annotations
import tensorflow as tf
from keras.saving import register_keras_serializable

@register_keras_serializable(package="src.PoCs.MultiModalTraining.model_restore", name="SpecAugment")
class SpecAugment(tf.keras.layers.Layer):
    """
    Stub de compatibilidade: aceita os mesmos kwargs do modelo salvo
    e retorna a entrada sem alterações (identidade).
    """
    def __init__(
        self,
        freq_mask_param: int | None = None,
        time_mask_param: int | None = None,
        num_freq_masks: int | None = None,
        num_time_masks: int | None = None,
        **kwargs,
    ):
        # Mantém compatibilidade com mixed_float16, dtype etc.
        super().__init__(**kwargs)
        # Guarda só para não perder durante get_config (não usado na inferência)
        self.freq_mask_param = freq_mask_param
        self.time_mask_param = time_mask_param
        self.num_freq_masks = num_freq_masks
        self.num_time_masks = num_time_masks

    def call(self, inputs, training=None):
        # Não aplica nada na inferência; se quiser aplicar só em training, poderia condicionar por `if training:`
        return inputs

    def get_config(self):
        base = super().get_config()
        base.update({
            "freq_mask_param": self.freq_mask_param,
            "time_mask_param": self.time_mask_param,
            "num_freq_masks": self.num_freq_masks,
            "num_time_masks": self.num_time_masks,
        })
        return base
