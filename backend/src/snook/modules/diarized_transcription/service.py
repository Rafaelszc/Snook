from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from snook.core import files
from snook.core.errors import AppError
from snook.core.events import EventBus, MeetingCreated, RetryRequested
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.diarized_transcription import messages, repository
from snook.modules.diarized_transcription.dispatcher import TREATED_FILE
from snook.modules.diarized_transcription.dispatcher import (
    TranscriptionDispatcher as TranscriptionDispatcher,
)
from snook.modules.diarized_transcription.engines.audio import AudioClipError as AudioClipError
from snook.modules.diarized_transcription.engines.audio import FfmpegAudio
from snook.modules.diarized_transcription.engines.base import Engines
from snook.modules.diarized_transcription.engines.hub import ModelSource
from snook.modules.diarized_transcription.engines.pyannote import PyannoteDiarizer
from snook.modules.diarized_transcription.engines.whisper import WhisperTranscriber, repo_for
from snook.modules.diarized_transcription.merge import Segment, Speaker, speakers
from snook.modules.diarized_transcription.schemas import SegmentOut, TranscriptOut
from snook.modules.meetings import service as meetings


def build_transcriber(settings: Settings) -> WhisperTranscriber:
    source = ModelSource(
        repo_id=repo_for(settings.whisper_model),
        revision=settings.whisper_revision,
        models_root=settings.models_root,
        offline=settings.models_offline,
    )
    return WhisperTranscriber(source=source, compute_type=settings.whisper_compute_type)


def build_diarizer(settings: Settings) -> PyannoteDiarizer:
    source = ModelSource(
        repo_id=settings.pyannote_pipeline,
        revision=settings.pyannote_revision,
        models_root=settings.models_root,
        offline=settings.models_offline,
    )
    return PyannoteDiarizer(source=source, token=settings.hf_token)


def build_engines(settings: Settings) -> Engines:
    """Engines reais. Atravessam o `spawn` por pickle: só parâmetros, sem banco nem modelo."""
    return Engines(
        audio=FfmpegAudio(),
        diarizer=build_diarizer(settings),
        transcriber=build_transcriber(settings),
    )


def download_models(
    settings: Settings,
    *,
    transcriber: WhisperTranscriber | None = None,
    diarizer: PyannoteDiarizer | None = None,
) -> None:
    """`download-models`: Whisper e Pyannote em revisão fixa no cache `/models` (ADR-0014).
    O cache do HuggingFace não baixa de novo o que já tem. Falha: `EngineFailure`."""
    (transcriber or build_transcriber(settings)).download()
    (diarizer or build_diarizer(settings)).download()


def build_dispatcher(settings: Settings, now: Callable[[], datetime]) -> TranscriptionDispatcher:
    return TranscriptionDispatcher(
        engines=build_engines(settings),
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


def segment_ids(uow: UnitOfWork, meeting_id: str) -> list[int]:
    """Ids na ordem de "Segmentos": a posição na lista é a mesma."""
    return [s.id for s in repository.list_segments(uow.session, meeting_id)]


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


def get_transcript(uow: UnitOfWork, *, user_id: str, meeting_id: str) -> TranscriptOut:
    """Dono conferido (404). Antes de `transcribed`, ou `failed` na transcrição: 409."""
    meeting = meetings.get_owned_meeting(uow, user_id, meeting_id)
    if meeting.status in {"pending", "processing"} or (
        meeting.status == "failed" and meeting.failed_stage == "transcription"
    ):
        raise AppError("transcript_not_ready", messages.TRANSCRIPT_NOT_READY, 409)
    return TranscriptOut(
        segments=[
            SegmentOut(
                id=s.id,
                speaker_label=s.speaker_label,
                start_seconds=s.start_seconds,
                end_seconds=s.end_seconds,
                text=s.text,
            )
            for s in repository.list_segments(uow.session, meeting_id)
        ]
    )
