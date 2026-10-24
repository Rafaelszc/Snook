"""Transcrição com faster-whisper `large-v3-turbo` (ADR-0014). Idioma fixo `pt`, VAD ligado,
modelo de repositório e revisão fixos em `/models` (SEC-22). Bibliotecas importadas só no
subprocesso: o backend e os testes padrão não carregam o modelo."""

import logging
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines import hub
from snook.modules.diarized_transcription.engines.base import LANGUAGE, Chunk, EngineFailure

logger = logging.getLogger("snook.transcription.whisper")

# Repositório oficial que o faster-whisper usa para o nome curto (`faster_whisper.utils`).
# `mobiuslabsgmbh/faster-whisper-large-v3-turbo` foi renomeado; o HuggingFace redireciona.
REPOS = {"large-v3-turbo": "dropbox-dash/faster-whisper-large-v3-turbo"}


def repo_for(model: str) -> str:
    """Nome curto conhecido ou id `dono/repo` (formato conferido no settings)."""
    return REPOS.get(model, model)


class _Segment(Protocol):
    start: float
    end: float
    text: str


class _Model(Protocol):
    def transcribe(self, audio: str, **options: Any) -> tuple[Iterable[_Segment], Any]: ...


def fetch_model(source: hub.ModelSource) -> str:
    """Pasta do modelo no cache; baixa se faltar e não estiver offline."""
    from faster_whisper import download_model

    path: str = download_model(
        source.repo_id,
        local_files_only=source.offline,
        cache_dir=str(source.cache_dir),
        revision=source.revision,
    )
    return path


def load_model(path: str, compute_type: str) -> _Model:
    from faster_whisper import WhisperModel

    model: _Model = WhisperModel(path, device="auto", compute_type=compute_type)
    return model


@dataclass(frozen=True)
class WhisperTranscriber:
    source: hub.ModelSource
    compute_type: str
    fetch: Callable[[hub.ModelSource], str] = fetch_model
    load: Callable[[str, str], _Model] = load_model

    def download(self) -> None:
        """`download-models`: só baixa para o cache, sem carregar."""
        hub.configure(self.source.models_root, self.source.offline)
        self.fetch(self.source)

    def transcribe(self, audio: Path, language: str) -> list[Chunk]:
        if language != LANGUAGE:
            raise ValueError("idioma fixo pt (`diarized-transcription` 8)")
        hub.configure(self.source.models_root, self.source.offline)
        try:
            path = self.fetch(self.source)
        except Exception as exc:
            # Mensagem do HuggingFace pode citar URL; só o tipo vai ao log (SEC-20).
            logger.warning("whisper.fetch_failed", extra={"error": type(exc).__name__})
            raise EngineFailure(messages.MODELS_UNAVAILABLE) from None
        try:
            model = self.load(path, self.compute_type)
            # Sem detecção de idioma: `language` sempre informado.
            segments, _info = model.transcribe(str(audio), language=language, vad_filter=True)
            chunks = [
                Chunk(float(s.start), float(s.end), s.text.strip())
                for s in segments
                if s.text.strip()
            ]
        except Exception as exc:
            logger.warning("whisper.failed", extra={"error": type(exc).__name__})
            raise EngineFailure(messages.TRANSCRIPTION_FAILED) from None
        return chunks
