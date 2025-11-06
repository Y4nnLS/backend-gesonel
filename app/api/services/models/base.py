from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Optional

class BaseEmotionModel(ABC):
    name: str
    version: str

    def __init__(self, device: Optional[str] = None):
        self.device = device or "cpu"
        self._loaded = False

    @abstractmethod
    def load(self) -> None:
        """Carrega pesos/artefatos em memória. Deve ser idempotente."""
        ...

    @abstractmethod
    def predict(self, file_path: str) -> Dict[str, float]:
        """Retorna {'anger':0.12, 'happy':0.41, ...} com softmax."""
        ...

    def ensure_loaded(self):
        if not self._loaded:
            self.load()
            self._loaded = True
