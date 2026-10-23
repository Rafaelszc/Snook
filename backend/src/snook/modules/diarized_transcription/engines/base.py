"""Interfaces de tratamento, diarização e transcrição (RT-13). Rodam no subprocesso: recebem só
caminho de arquivo e parâmetros, nunca tocam o banco (`03-security.md`, fronteira 3)."""

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

LANGUAGE = "pt"  # fixo, sem detecção automática (`diarized-transcription` 8)


@dataclass(frozen=True)
class Turn:
    """Turno da diarização."""

    speaker_label: str
    start_seconds: float
    end_seconds: float


@dataclass(frozen=True)
class Chunk:
    """Trecho do Whisper, ainda sem speaker."""

    start_seconds: float
    end_seconds: float
    text: str


class EngineFailure(Exception):
    """Falha esperada de uma engine. `message` vai ao usuário: pt-BR, sem segredo (SEC-20)."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class AudioTreater(Protocol):
    def treat(self, source: Path, target: Path) -> None: ...


class Diarizer(Protocol):
    def diarize(self, audio: Path, num_speakers: int | None) -> list[Turn]: ...


class Transcriber(Protocol):
    def transcribe(self, audio: Path, language: str) -> list[Chunk]: ...


@dataclass(frozen=True)
class Engines:
    audio: AudioTreater
    diarizer: Diarizer
    transcriber: Transcriber
