from collections.abc import Callable
from datetime import datetime

from snook.core.events import EventBus, MeetingCreated, RetryRequested
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import repository
from snook.modules.diarized_transcription.dispatcher import (
    TranscriptionDispatcher as TranscriptionDispatcher,
)
from snook.modules.diarized_transcription.merge import Segment
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
