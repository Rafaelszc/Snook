from sqlalchemy import Float, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base


class TranscriptPart(Base):
    """Parte da Transcrição: segmentos contíguos de `first` a `last` (04-data-model).
    `start_seconds` e `end_seconds` absolutos na gravação."""

    __tablename__ = "transcript_parts"
    __table_args__ = (UniqueConstraint("meeting_id", "index", name="uq_transcript_parts_index"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    index: Mapped[int]
    first_segment_id: Mapped[int] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    last_segment_id: Mapped[int] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    estimated_tokens: Mapped[int]
