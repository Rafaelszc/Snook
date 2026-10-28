from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base

NAME_MAX = 100


class Participant(Base):
    """Pessoa nomeada numa Reunião. `name` já aparado; `name_norm` compara (04-data-model)."""

    __tablename__ = "participants"
    __table_args__ = (
        UniqueConstraint("meeting_id", "name_norm", name="uq_participants_meeting_name"),
        CheckConstraint("length(name) BETWEEN 1 AND 100", name="ck_participants_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX))
    name_norm: Mapped[str] = mapped_column(String)


class SpeakerLink(Base):
    """Um `speaker_label` da Reunião aponta para um só Participante."""

    __tablename__ = "speaker_links"

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    speaker_label: Mapped[str] = mapped_column(String, primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id", ondelete="CASCADE"))
