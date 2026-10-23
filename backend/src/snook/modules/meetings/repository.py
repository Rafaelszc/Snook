from sqlalchemy.orm import Session

from snook.modules.meetings.models import Meeting


def add_meeting(session: Session, meeting: Meeting) -> None:
    session.add(meeting)
    session.flush()


def get_meeting(session: Session, meeting_id: str) -> Meeting | None:
    return session.get(Meeting, meeting_id)
