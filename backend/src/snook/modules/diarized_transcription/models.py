from sqlalchemy import Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base


class TranscriptSegment(Base):
    """Segmento da Transcrição. `0 <= start < end <= duração` e texto não vazio: checados na
    aplicação (04-data-model)."""

    __tablename__ = "transcript_segments"
    __table_args__ = (
        UniqueConstraint("meeting_id", "position", name="uq_transcript_segments_position"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    position: Mapped[int]
    speaker_label: Mapped[str] = mapped_column(String)
    start_seconds: Mapped[float] = mapped_column(Float)
    end_seconds: Mapped[float] = mapped_column(Float)
    text: Mapped[str] = mapped_column(String)
