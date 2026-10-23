from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from snook.core import files
from snook.core.events import EventBus, MeetingCreated, RetryRequested
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import repository
from snook.modules.diarized_transcription.dispatcher import TREATED_FILE
from snook.modules.diarized_transcription.dispatcher import (
    TranscriptionDispatcher as TranscriptionDispatcher,
)
from snook.modules.diarized_transcription.engines.audio import AudioClipError as AudioClipError
from snook.modules.diarized_transcription.engines.audio import FfmpegAudio
from snook.modules.diarized_transcription.merge import Segment, Speaker, speakers
from snook.modules.diarized_transcription.pipeline import default_engines


def build_dispatcher(settings: Settings, now: Callable[[], datetime]) -> TranscriptionDispatcher:
    return TranscriptionDispatcher(
        engines=default_engines(),
        workers=settings.transcription_workers,
        max_per_user=settings.transcription_max_per_user,
        audio_root=settings.audio_root,
        now=now,
    )


def subscribe(bus: EventBus, dispatcher: Callable[[], TranscriptionDispatcher]) -> None:
    """Consome `MeetingCreated` e `RetryRequested(transcription)` (02-architecture, "Avisos")."""
    bus.subscribe(MeetingCreated, lambda event: dispatcher().on_event(event))
    bus.subscribe(RetryRequested, lambda event: dispatcher().on_event(event))


def list_segments(uow: UnitOfWork, meeting_id: str) -> list[Segment]:
    """Interface "Segmentos": em ordem de início; vazia antes de `transcribed`."""
    return [
        Segment(s.speaker_label, s.start_seconds, s.end_seconds, s.text)
        for s in repository.list_segments(uow.session, meeting_id)
    ]


def list_speakers(uow: UnitOfWork, meeting_id: str) -> list[Speaker]:
    """Interface "Speakers": rótulos dos segmentos, com tempo total e maior segmento."""
    return speakers(list_segments(uow, meeting_id))


def treated_audio_clip(
    audio_root: Path, meeting_id: str, start: float, end: float, *, audio: FfmpegAudio | None = None
) -> bytes:
    """Interface "Áudio tratado": trecho em WAV. Dono já conferido por quem chama.
    Sem `treated.flac` (antes de `transcribed`) ou ffmpeg falhou: `AudioClipError`."""
    source = files.meeting_dir(audio_root, meeting_id) / TREATED_FILE  # checagens de SEC-15
    if not source.is_file():
        raise AudioClipError
    target = files.new_tmp_path(audio_root).with_suffix(".wav")
    try:
        (audio or FfmpegAudio()).clip(source, target, start, end)
        return target.read_bytes()
    finally:
        files.discard_tmp(audio_root, target)
