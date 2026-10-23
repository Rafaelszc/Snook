from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from snook.core.clock import to_iso
from snook.modules.meetings import messages
from snook.modules.meetings.models import STATUS_FAILED, STATUS_PENDING, Meeting

# Q58, Q69: status em andamento ao cair e a etapa que retoma.
_INTERRUPTED_STAGE = {"processing": "transcription", "generating": "generation"}


def mark_interrupted(session: Session, now: datetime) -> list[Meeting]:
    """Leva a `failed` o que estava em andamento. Sem aviso; `run_id` antigo fica velho."""
    query = select(Meeting).where(
        or_(
            Meeting.status.in_(_INTERRUPTED_STAGE),
            (Meeting.status == "transcribed") & Meeting.participants_confirmed_at.is_not(None),
        )
    )
    meetings = list(session.scalars(query))
    stamp = to_iso(now)
    for meeting in meetings:
        meeting.failed_stage = _INTERRUPTED_STAGE.get(meeting.status, "generation")
        meeting.status = STATUS_FAILED
        meeting.error_message = messages.INTERRUPTED
        meeting.updated_at = stamp
    session.flush()
    return meetings


def pending_in_creation_order(session: Session) -> list[Meeting]:
    query = (
        select(Meeting)
        .where(Meeting.status == STATUS_PENDING)
        .order_by(Meeting.created_at, Meeting.id)
    )
    return list(session.scalars(query))
