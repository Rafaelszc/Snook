from sqlalchemy import func, select
from sqlalchemy.orm import Session

from snook.modules.meetings.models import Meeting


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


def count_by_user(session: Session, status: str) -> dict[str, int]:
    query = (
        select(Meeting.user_id, func.count())
        .where(Meeting.status == status)
        .group_by(Meeting.user_id)
    )
    return {user_id: count for user_id, count in session.execute(query)}
