import uuid
from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, String, Integer, Numeric, Index, DateTime, JSON
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class Base(DeclarativeBase):
    pass

class AudioFile(Base):
    __tablename__ = "audio_file"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True)
    rel_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    format: Mapped[str | None] = mapped_column(String(8))
    duration_s: Mapped[float | None] = mapped_column(Numeric(8, 3))
    sample_rate: Mapped[int | None] = mapped_column(Integer)
    channels: Mapped[int | None] = mapped_column(Integer)
    dataset: Mapped[str | None] = mapped_column(String(64))
    speaker_id: Mapped[str | None] = mapped_column(String(64))
    emotion_label: Mapped[str | None] = mapped_column(String(32))
    split: Mapped[str | None] = mapped_column(String(8))
    augment_pipeline: Mapped[str | None] = mapped_column(Text)

    # Status/processamento geral
    processing_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending|processing|completed|failed
    processing_error: Mapped[str | None] = mapped_column(Text)
    processing_metadata: Mapped[dict | None] = mapped_column(JSON)

    # Resultado "agregado" (se quiser manter para retrocompatibilidade / quick view)
    predicted_emotion: Mapped[str | None] = mapped_column(String(32))
    confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))

    # ===== Campos específicos por modelo =====
    # 1) CNN 1D
    model1d_status: Mapped[str | None] = mapped_column(String(20))              # pending|processing|done|error
    model1d_predicted_emotion: Mapped[str | None] = mapped_column(String(32))
    model1d_confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    model1d_probs: Mapped[dict | None] = mapped_column(JSON)                    # {"happy":0.82,"sad":0.05,...}
    model1d_segments: Mapped[dict | None] = mapped_column(JSON)                 # janelas/trechos
    model1d_metadata: Mapped[dict | None] = mapped_column(JSON)                 # MFCCs, tempos, etc.

    # 2) MultiModal
    mm_status: Mapped[str | None] = mapped_column(String(20))                   # pending|processing|done|error
    mm_predicted_emotion: Mapped[str | None] = mapped_column(String(32))
    mm_confidence_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    mm_probs: Mapped[dict | None] = mapped_column(JSON)
    mm_segments: Mapped[dict | None] = mapped_column(JSON)
    mm_metadata: Mapped[dict | None] = mapped_column(JSON)                      # audio_emb, text_emb, etc.

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

Index("ix_audio_rel_path", AudioFile.rel_path)
Index("ix_audio_dataset", AudioFile.dataset)
Index("ix_audio_label", AudioFile.emotion_label)
Index("ix_audio_status", AudioFile.processing_status)

# Índices úteis por modelo
Index("ix_audio_model1d_status", AudioFile.model1d_status)
Index("ix_audio_mm_status", AudioFile.mm_status)
