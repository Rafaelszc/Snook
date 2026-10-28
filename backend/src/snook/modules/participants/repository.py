from sqlalchemy import select
from sqlalchemy.orm import Session

from snook.modules.participants.models import Participant, SpeakerLink


def add_participant(session: Session, meeting_id: str, name: str, name_norm: str) -> Participant:
    participant = Participant(meeting_id=meeting_id, name=name, name_norm=name_norm)
    session.add(participant)
    session.flush()
    return participant


def link_speaker(
    session: Session, meeting_id: str, speaker_label: str, participant_id: int
) -> None:
    session.add(
        SpeakerLink(
            meeting_id=meeting_id, speaker_label=speaker_label, participant_id=participant_id
        )
    )
    session.flush()


def list_participants(session: Session, meeting_id: str) -> list[Participant]:
    query = select(Participant).where(Participant.meeting_id == meeting_id).order_by(Participant.id)
    return list(session.scalars(query))


def list_links(session: Session, meeting_id: str) -> list[SpeakerLink]:
    query = (
        select(SpeakerLink)
        .where(SpeakerLink.meeting_id == meeting_id)
        .order_by(SpeakerLink.speaker_label)
    )
    return list(session.scalars(query))


def participant_for_speaker(
    session: Session, meeting_id: str, speaker_label: str
) -> Participant | None:
    query = (
        select(Participant)
        .join(SpeakerLink, SpeakerLink.participant_id == Participant.id)
        .where(SpeakerLink.meeting_id == meeting_id, SpeakerLink.speaker_label == speaker_label)
    )
    return session.scalars(query).one_or_none()
