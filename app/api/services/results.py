# app/services/results.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, Any, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import update
from ..models.audio_file import AudioFile  # ajuste o import

def _dec(x: Optional[float]) -> Optional[Decimal]:
    return None if x is None else Decimal(str(x))

def save_1d_result(
    db: Session,
    audio_id: UUID,
    *,
    probs: Dict[str, float],                 # {"happy":0.82,...}
    top_label: Optional[str] = None,         # se None, calculo do probs
    confidence: Optional[float] = None,      # 0..1; se None, calculo do probs
    segments: Optional[Any] = None,
    metadata: Optional[dict] = None,
    status: str = "done",                    # "done" | "error" | "processing"
    error_message: Optional[str] = None,
) -> None:
    if not probs:
        probs = {}
    if top_label is None and probs:
        top_label = max(probs, key=probs.get)
    if confidence is None and top_label is not None:
        confidence = float(probs.get(top_label, 0.0))

    stmt = (
        update(AudioFile)
        .where(AudioFile.id == audio_id)
        .values(
            model1d_status=status,
            model1d_predicted_emotion=top_label,
            model1d_confidence_score=_dec(confidence),
            model1d_probs=probs or None,
            model1d_segments=segments,
            model1d_metadata=metadata,
            # opcional: erro só se veio algo
            processing_error=error_message if error_message else None,
        )
    )
    db.execute(stmt)
    db.commit()

def save_mm_result(
    db: Session,
    audio_id: UUID,
    *,
    probs: Dict[str, float],
    top_label: Optional[str] = None,
    confidence: Optional[float] = None,
    segments: Optional[Any] = None,
    metadata: Optional[dict] = None,
    status: str = "done",
    error_message: Optional[str] = None,
) -> None:
    if not probs:
        probs = {}
    if top_label is None and probs:
        top_label = max(probs, key=probs.get)
    if confidence is None and top_label is not None:
        confidence = float(probs.get(top_label, 0.0))

    stmt = (
        update(AudioFile)
        .where(AudioFile.id == audio_id)
        .values(
            mm_status=status,
            mm_predicted_emotion=top_label,
            mm_confidence_score=_dec(confidence),
            mm_probs=probs or None,
            mm_segments=segments,
            mm_metadata=metadata,
            processing_error=error_message if error_message else None,
        )
    )
    db.execute(stmt)
    db.commit()


# from app.services.results import save_mm_result
# save_mm_result(
#     db,
#     audio_id,
#     probs=mm_scores,
#     status="done",
#     segments=mm_segments,          # se tiver
#     metadata={"text_emb":"...", "audio_emb":"..."}  # se tiver
# )