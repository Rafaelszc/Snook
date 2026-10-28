from pathlib import Path

from snook.core.errors import AppError
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import service as transcription
from snook.modules.meetings import service as meetings
from snook.modules.participants import messages
from snook.modules.participants.schemas import SpeakerOut

SAMPLE_MAX_SECONDS = 10.0


def _ensure_transcribed(uow: UnitOfWork, user_id: str, meeting_id: str) -> None:
    """Dono conferido (404). Antes de `transcribed`, ou `failed` na transcrição: 409."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.status in {"pending", "processing"} or (
        meeting.status == "failed" and meeting.failed_stage == "transcription"
    ):
        raise AppError("speakers_not_ready", messages.SPEAKERS_NOT_READY, 409)


def list_speakers(uow: UnitOfWork, *, user_id: str, meeting_id: str) -> list[SpeakerOut]:
    """Cada rótulo uma vez, com tempo total de fala (`participants` 1)."""
    _ensure_transcribed(uow, user_id, meeting_id)
    return [
        SpeakerOut(speaker_label=s.speaker_label, total_seconds=s.total_seconds)
        for s in transcription.list_speakers(uow, meeting_id)
    ]


def speaker_sample(
    uow: UnitOfWork, audio_root: Path, *, user_id: str, meeting_id: str, speaker_label: str
) -> bytes:
    """WAV de até 10 s do início do maior segmento; empate: o que começa antes (`participants`
    2 a 5). Sob demanda, sem cache. Rótulo ausente, ou áudio tratado indisponível: 404."""
    meetings.get_owned_meeting(uow, user_id, meeting_id)
    speaker = next(
        (
            s
            for s in transcription.list_speakers(uow, meeting_id)
            if s.speaker_label == speaker_label
        ),
        None,
    )
    if speaker is None:
        raise AppError("speaker_not_found", messages.SPEAKER_NOT_FOUND, 404)
    start = speaker.longest.start_seconds
    end = min(speaker.longest.end_seconds, start + SAMPLE_MAX_SECONDS)
    try:
        return transcription.treated_audio_clip(audio_root, meeting_id, start, end)
    except transcription.AudioClipError:
        raise AppError("sample_unavailable", messages.SAMPLE_UNAVAILABLE, 404) from None
