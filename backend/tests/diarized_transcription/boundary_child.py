"""Código que roda no subprocesso `spawn` do teste de fronteira. Imports mínimos: o que o filho
carrega aqui é o que o trabalho real carrega (sem banco, sem app)."""

import socket
import sys
from pathlib import Path
from typing import Any

from pydantic import SecretStr

from snook.modules.diarized_transcription.engines.base import Engines
from snook.modules.diarized_transcription.engines.hub import ModelSource
from snook.modules.diarized_transcription.pipeline import Job, run_job


class CopyAudio:
    """Tratamento falso: copia o original para o temporário (sem ffmpeg)."""

    def treat(self, source: Path, target: Path, duration_seconds: float) -> None:
        target.write_bytes(source.read_bytes())


class _Segment:
    def __init__(self, start: float, end: float, text: str = "") -> None:
        self.start, self.end, self.text = start, end, text


class _Model:
    def transcribe(self, audio: str, **options: Any) -> tuple[list[_Segment], None]:
        Path(audio).read_bytes()
        return [_Segment(0.5, 4.5, "Bom dia."), _Segment(5.5, 9.5, "Até logo.")], None


class _Annotation:
    def itertracks(self, yield_label: bool) -> list[tuple[_Segment, str, str]]:
        return [(_Segment(0.0, 5.0), "A", "SPEAKER_00"), (_Segment(5.0, 10.0), "B", "SPEAKER_01")]


class _Pipeline:
    def __call__(self, audio: dict[str, Any], **options: Any) -> _Annotation:
        return _Annotation()


def fetch(source: ModelSource) -> str:
    return str(source.cache_dir / "whisper")


def load_whisper(path: str, compute_type: str) -> _Model:
    return _Model()


def load_pyannote(source: ModelSource, token: SecretStr | None) -> _Pipeline:
    return _Pipeline()


def decode(audio: Path) -> dict[str, Any]:
    return {"waveform": audio.read_bytes(), "sample_rate": 16000}


def run_guarded(engines: Engines, job: Job) -> dict[str, Any]:
    """Roda o trabalho com a rede bloqueada e conta as tentativas de conexão."""
    attempts: list[object] = []

    def refuse(*args: object, **_kwargs: object) -> None:
        attempts.append(args[1:] if len(args) > 1 else args)
        raise OSError("rede bloqueada no teste")

    socket.socket.connect = refuse  # type: ignore[method-assign]
    socket.socket.connect_ex = refuse  # type: ignore[method-assign,assignment]
    socket.create_connection = refuse  # type: ignore[assignment]
    socket.getaddrinfo = refuse  # type: ignore[assignment]
    segments = run_job(engines, job)
    return {
        "segments": len(segments),
        "network_attempts": len(attempts),
        "db_modules": sorted(
            name for name in sys.modules if name.startswith(("sqlalchemy", "snook.core.db"))
        ),
        "app_modules": sorted(
            name for name in sys.modules if name.startswith(("fastapi", "snook.main"))
        ),
    }
