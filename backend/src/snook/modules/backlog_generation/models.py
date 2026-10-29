from sqlalchemy import CheckConstraint, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base


class Epic(Base):
    """Epic da Reunião. `name` já aparado; `name_norm` junta Epics de mesmo nome (Q57)."""

    __tablename__ = "epics"
    __table_args__ = (
        UniqueConstraint("meeting_id", "name_norm", name="uq_epics_meeting_name"),
        CheckConstraint("length(name) BETWEEN 1 AND 200", name="ck_epics_name"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(200))
    name_norm: Mapped[str] = mapped_column(String)
    position: Mapped[int]


class UserStory(Base):
    """`us_number` exibido como `US-01`. `requested_by` `SET NULL` só como rede de segurança:
    a união de Participantes troca o solicitante antes (04-data-model)."""

    __tablename__ = "user_stories"
    __table_args__ = (
        UniqueConstraint("meeting_id", "us_number", name="uq_user_stories_number"),
        CheckConstraint("length(name) BETWEEN 1 AND 200", name="ck_user_stories_name"),
        CheckConstraint(
            "length(as_a) BETWEEN 1 AND 2000 AND length(i_want) BETWEEN 1 AND 2000 "
            "AND length(so_that) BETWEEN 1 AND 2000",
            name="ck_user_stories_text",
        ),
        CheckConstraint("priority IN ('Low', 'Medium', 'High')", name="ck_user_stories_priority"),
        CheckConstraint("story_points IN (1, 2, 3, 5, 8, 13)", name="ck_user_stories_story_points"),
        CheckConstraint(
            "requested_at_seconds IS NULL OR requested_at_seconds >= 0",
            name="ck_user_stories_requested_at",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[str] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    epic_id: Mapped[int] = mapped_column(ForeignKey("epics.id", ondelete="CASCADE"))
    us_number: Mapped[int]
    name: Mapped[str] = mapped_column(String(200))
    as_a: Mapped[str] = mapped_column(String(2000))
    i_want: Mapped[str] = mapped_column(String(2000))
    so_that: Mapped[str] = mapped_column(String(2000))
    priority: Mapped[str] = mapped_column(String)
    story_points: Mapped[int]
    requested_by: Mapped[int | None] = mapped_column(
        ForeignKey("participants.id", ondelete="SET NULL")
    )
    requested_at_seconds: Mapped[int | None]
    position: Mapped[int]


class AcceptanceCriterion(Base):
    """`when_` e `then_`: nomes de coluna fora das palavras reservadas."""

    __tablename__ = "acceptance_criteria"
    __table_args__ = (
        CheckConstraint(
            "length(given) BETWEEN 1 AND 1000 AND length(when_) BETWEEN 1 AND 1000 "
            "AND length(then_) BETWEEN 1 AND 1000",
            name="ck_acceptance_criteria_text",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_story_id: Mapped[int] = mapped_column(ForeignKey("user_stories.id", ondelete="CASCADE"))
    given: Mapped[str] = mapped_column(String(1000))
    when_: Mapped[str] = mapped_column(String(1000))
    then_: Mapped[str] = mapped_column(String(1000))
    position: Mapped[int]


class BacklogCounter(Base):
    """Maior `us_number` já usado na Reunião. Não desce na exclusão; zera na regeneração (Q50)."""

    __tablename__ = "backlog_counters"

    meeting_id: Mapped[str] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), primary_key=True
    )
    last_us_number: Mapped[int]
