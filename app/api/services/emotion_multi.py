from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Dict, List, Tuple
from .models.registry import resolve_models, get_model

def infer_with_models(file_path: str, modelos: List[str]) -> Dict[str, dict]:
    results: Dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=min(4, len(modelos) or 1)) as pool:
        futures = {}
        for m in modelos:
            mdl = get_model(m)
            futures[pool.submit(_timed_predict, mdl, file_path)] = m

        for fut in as_completed(futures):
            name = futures[fut]
            try:
                top, scores, ms = fut.result()
                results[name] = {"top": top, "scores": scores, "latency_ms": ms}
            except Exception as e:
                results[name] = {"error": str(e)}
    return results

def _timed_predict(model, file_path: str) -> Tuple[str, dict, float]:
    t0 = perf_counter()
    scores = model.predict(file_path)
    top = max(scores, key=scores.get)
    return top, scores, (perf_counter() - t0) * 1000.0
