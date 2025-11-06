from __future__ import annotations
from functools import lru_cache
from typing import Dict, Iterable, List, Optional, Type

from .base import BaseEmotionModel
from .keras_model_1d import KerasEmotionModel
# from .MULTIMODAL import MULTIMODAL

_REGISTRY: Dict[str, Type[BaseEmotionModel]] = {
    KerasEmotionModel.name: KerasEmotionModel,
    # MULTIMODAL.name: MULTIMODAL,
}

def available_models() -> List[str]:
    return list(_REGISTRY.keys())

@lru_cache(maxsize=64)
def get_model(name: str) -> BaseEmotionModel:
    if name not in _REGISTRY:
        raise KeyError(f"Modelo não registrado: {name}")
    return _REGISTRY[name]()  # kwargs se necessário

def resolve_models(requested: Optional[Iterable[str]]) -> List[str]:
    if not requested or requested == ["all"] or (isinstance(requested, str) and requested == "all"):
        return available_models()
    return [m for m in requested if m in _REGISTRY]
