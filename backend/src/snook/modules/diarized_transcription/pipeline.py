"""Trabalho do subprocesso: tratar, diarizar, transcrever e juntar (02-architecture, passo 5).
Lê só o arquivo original e escreve só o temporário; não toca o banco."""

from dataclasses import dataclass
from pathlib import Path

from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines.audio import FfmpegAudio
from snook.modules.diarized_transcription.engines.base import (
    LANGUAGE,
    Chunk,
    EngineFailure,
    Engines,
    Turn,
)
from snook.modules.diarized_transcription.merge import Segment, merge


@dataclass(frozen=True)
class Job:
    original_path: Path
    treated_path: Path  # em `/audios/.tmp/`; vai para a Reunião só depois do commit
    duration_seconds: float
    expected_speakers: int | None


def run_job(engines: Engines, job: Job) -> list[Segment]:
    engines.audio.treat(job.original_path, job.treated_path, job.duration_seconds)
    turns = engines.diarizer.diarize(job.treated_path, job.expected_speakers)
    chunks = engines.transcriber.transcribe(job.treated_path, LANGUAGE)
    segments = merge(turns, chunks, job.duration_seconds)
    if not segments:
        raise EngineFailure(messages.NO_SPEECH)
    return segments


class _Unavailable:
    """Engine real ainda não instalada (Task 26): a Reunião falha com mensagem clara."""

    def diarize(self, audio: Path, num_speakers: int | None) -> list[Turn]:
        raise EngineFailure(messages.ENGINES_UNAVAILABLE)

    def transcribe(self, audio: Path, language: str) -> list[Chunk]:
        raise EngineFailure(messages.ENGINES_UNAVAILABLE)


def default_engines() -> Engines:
    unavailable = _Unavailable()
    return Engines(audio=FfmpegAudio(), diarizer=unavailable, transcriber=unavailable)
