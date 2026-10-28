from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from snook.modules.transcript_split.models import TranscriptPart


def replace_parts(session: Session, meeting_id: str, parts: list[TranscriptPart]) -> None:
    """Apaga todas as Partes da Reunião e grava as novas, na transação de quem chama."""
    session.execute(delete(TranscriptPart).where(TranscriptPart.meeting_id == meeting_id))
    session.flush()
    session.add_all(parts)
    session.flush()


def list_parts(session: Session, meeting_id: str) -> list[TranscriptPart]:
    query = (
        select(TranscriptPart)
        .where(TranscriptPart.meeting_id == meeting_id)
        .order_by(TranscriptPart.index)
    )
    return list(session.scalars(query))
