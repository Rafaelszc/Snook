from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from snook.modules.diarized_transcription.merge import Segment
from snook.modules.diarized_transcription.models import TranscriptSegment


def add_segments(session: Session, meeting_id: str, segments: list[Segment]) -> None:
    session.add_all(
        TranscriptSegment(
            meeting_id=meeting_id,
            position=position,
            speaker_label=segment.speaker_label,
            start_seconds=segment.start_seconds,
            end_seconds=segment.end_seconds,
            text=segment.text,
        )
        for position, segment in enumerate(segments)
    )
    session.flush()


def delete_segments(session: Session, meeting_id: str) -> None:
    session.execute(delete(TranscriptSegment).where(TranscriptSegment.meeting_id == meeting_id))


def list_segments(session: Session, meeting_id: str) -> list[TranscriptSegment]:
    query = (
        select(TranscriptSegment)
        .where(TranscriptSegment.meeting_id == meeting_id)
        .order_by(TranscriptSegment.position)
    )
    return list(session.scalars(query))
