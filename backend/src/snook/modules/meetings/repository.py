from collections.abc import Iterator

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from snook.modules.meetings.models import Meeting

_PENDING_BATCH = 20


def add_meeting(session: Session, meeting: Meeting) -> None:
    session.add(meeting)
    session.flush()


def get_meeting(session: Session, meeting_id: str) -> Meeting | None:
    return session.get(Meeting, meeting_id)


def list_meetings(session: Session, user_id: str) -> list[Meeting]:
    query = (
        select(Meeting)
        .where(Meeting.user_id == user_id)
        .order_by(Meeting.created_at.desc(), Meeting.id)
    )
    return list(session.scalars(query))


def delete_meeting(session: Session, meeting: Meeting) -> None:
    """FKs `ON DELETE CASCADE` levam os dados derivados (04-data-model)."""
    session.delete(meeting)
    session.flush()


def pending_below_limit(session: Session, max_per_user: int) -> Iterator[Meeting]:
    """`pending` em ordem de criação, só de Usuário com menos de `max_per_user` em `processing`."""
    busy_users = (
        select(Meeting.user_id)
        .where(Meeting.status == "processing")
        .group_by(Meeting.user_id)
        .having(func.count() >= max_per_user)
    )
    query = (
        select(Meeting)
        .where(Meeting.status == "pending", Meeting.user_id.not_in(busy_users))
        .order_by(Meeting.created_at, Meeting.id)
        .execution_options(yield_per=_PENDING_BATCH)
    )
    return iter(session.scalars(query))
