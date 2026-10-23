"""Engines falsas para o pytest: sem GPU, sem rede, sem modelo (RT-13, transversal 18)."""

import threading
from collections.abc import Callable
from concurrent.futures import Executor, Future
from pathlib import Path
from typing import Any, Literal, TypeVar

from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines.base import Chunk, EngineFailure, Engines, Turn

T = TypeVar("T")
Outcome = Literal[
    "ok", "audio_failure", "diarization_failure", "transcription_failure", "no_speech", "hf_token"
]
HOLD_TIMEOUT_SECONDS = 10.0

TURNS = [Turn("SPEAKER_00", 0.0, 5.0), Turn("SPEAKER_01", 5.0, 10.0)]
CHUNKS = [Chunk(0.5, 4.5, "Bom dia, vamos começar."), Chunk(5.5, 9.5, "Preciso de um relatório.")]


class FakeAudio:
    """Escreve um FLAC falso. Com `hold`, cada Reunião espera `release(meeting_id)`."""

    def __init__(self, outcome: Outcome, hold: bool) -> None:
        self.outcome = outcome
        self.hold = hold
        self.sources: list[Path] = []
        self._lock = threading.Lock()
        self._started: dict[str, threading.Event] = {}
        self._gates: dict[str, threading.Event] = {}

    def _gate(self, store: dict[str, threading.Event], meeting_id: str) -> threading.Event:
        with self._lock:
            return store.setdefault(meeting_id, threading.Event())

    def treat(self, source: Path, target: Path) -> None:
        meeting_id = source.parent.name
        self.sources.append(source)
        self._gate(self._started, meeting_id).set()
        if self.hold and not self._gate(self._gates, meeting_id).wait(HOLD_TIMEOUT_SECONDS):
            raise TimeoutError(f"fake não liberado: {meeting_id}")
        if self.outcome == "audio_failure":
            raise EngineFailure(messages.AUDIO_FAILED)
        target.write_bytes(b"fLaC tratado falso")

    def wait_started(self, meeting_id: str) -> bool:
        return self._gate(self._started, meeting_id).wait(HOLD_TIMEOUT_SECONDS)

    def started(self, meeting_id: str) -> bool:
        return self._gate(self._started, meeting_id).is_set()

    def release(self, meeting_id: str) -> None:
        self._gate(self._gates, meeting_id).set()

    def release_all(self) -> None:
        self.hold = False
        with self._lock:
            gates = list(self._gates.values())
        for gate in gates:
            gate.set()


class FakeDiarizer:
    def __init__(self, outcome: Outcome, turns: list[Turn]) -> None:
        self.outcome = outcome
        self.turns = turns
        self.calls: list[int | None] = []

    def diarize(self, audio: Path, num_speakers: int | None) -> list[Turn]:
        self.calls.append(num_speakers)
        if self.outcome == "hf_token":
            raise EngineFailure(messages.HF_ACCESS_DENIED)
        if self.outcome == "diarization_failure":
            raise EngineFailure(messages.DIARIZATION_FAILED)
        return list(self.turns)


class FakeTranscriber:
    def __init__(self, outcome: Outcome, chunks: list[Chunk]) -> None:
        self.outcome = outcome
        self.chunks = chunks
        self.languages: list[str] = []

    def transcribe(self, audio: Path, language: str) -> list[Chunk]:
        self.languages.append(language)
        if self.outcome == "transcription_failure":
            raise EngineFailure(messages.TRANSCRIPTION_FAILED)
        if self.outcome == "no_speech":
            return []
        return list(self.chunks)


class FakeEngines(Engines):
    audio: FakeAudio
    diarizer: FakeDiarizer
    transcriber: FakeTranscriber


def fake_engines(
    outcome: Outcome = "ok",
    *,
    hold: bool = False,
    turns: list[Turn] | None = None,
    chunks: list[Chunk] | None = None,
) -> FakeEngines:
    return FakeEngines(
        audio=FakeAudio(outcome, hold),
        diarizer=FakeDiarizer(outcome, TURNS if turns is None else turns),
        transcriber=FakeTranscriber(outcome, CHUNKS if chunks is None else chunks),
    )


class SyncExecutor(Executor):
    """Roda na hora, na thread de quem chama: pipeline síncrono nos testes."""

    def submit(self, fn: Callable[..., T], /, *args: Any, **kwargs: Any) -> "Future[T]":
        future: Future[T] = Future()
        try:
            future.set_result(fn(*args, **kwargs))
        except BaseException as exc:  # o Future leva a exceção, como num executor real
            future.set_exception(exc)
        return future
