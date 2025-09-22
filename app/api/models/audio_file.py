import uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Text, String, Integer, Numeric, Index
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

Index("ix_audio_rel_path", AudioFile.rel_path)
Index("ix_audio_dataset", AudioFile.dataset)
Index("ix_audio_label", AudioFile.emotion_label)
