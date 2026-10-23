import time
from collections.abc import Callable, Iterator
from concurrent.futures import Executor, ThreadPoolExecutor

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.modules.diarized_transcription.dispatcher import TranscriptionDispatcher
from snook.modules.diarized_transcription.engines.fakes import (
    FakeEngines,
    SyncExecutor,
    fake_engines,
)
from tests.meetings.conftest import ana, clock, probe, uow, users  # noqa: F401

WAIT_SECONDS = 5.0


def wait_for(condition: Callable[[], bool], timeout: float = WAIT_SECONDS) -> None:
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            raise AssertionError("condição não chegou a tempo")
        time.sleep(0.01)


def install(
    client: TestClient,
    engines: FakeEngines,
    executor_factory: Callable[[int], Executor],
    *,
    workers: int,
    max_per_user: int,
) -> TranscriptionDispatcher:
    """Troca o dispatcher inerte por um real, com engines falsas, na app já de pé."""
    app: FastAPI = client.app  # type: ignore[assignment]
    settings: Settings = app.state.settings
    dispatcher = TranscriptionDispatcher(
        engines=engines,
        workers=workers,
        max_per_user=max_per_user,
        audio_root=settings.audio_root,
        now=lambda: app.state.clock.now(),
        executor_factory=executor_factory,
    )
    app.state.transcription.stop()
    app.state.transcription = dispatcher
    dispatcher.start(app.state.session_factory, app.state.event_bus.publish)
    return dispatcher


@pytest.fixture
def engines() -> FakeEngines:
    return fake_engines()


@pytest.fixture
def dispatcher(
    client: TestClient, settings: Settings, engines: FakeEngines
) -> TranscriptionDispatcher:
    """Pipeline síncrono: o upload volta com a transcrição já terminada."""
    return install(
        client,
        engines,
        lambda _workers: SyncExecutor(),
        workers=settings.transcription_workers,
        max_per_user=settings.transcription_max_per_user,
    )


@pytest.fixture
def held() -> Iterator[FakeEngines]:
    """Engines que só terminam quando o teste libera cada Reunião."""
    engines = fake_engines(hold=True)
    yield engines
    engines.audio.release_all()


@pytest.fixture
def threaded(
    client: TestClient, held: FakeEngines
) -> Iterator[Callable[..., TranscriptionDispatcher]]:
    """Dispatcher com threads de verdade, para checar concorrência e limites."""
    pools: list[ThreadPoolExecutor] = []

    def factory(workers: int) -> Executor:
        pool = ThreadPoolExecutor(max_workers=workers)
        pools.append(pool)
        return pool

    def make(*, workers: int, max_per_user: int) -> TranscriptionDispatcher:
        return install(client, held, factory, workers=workers, max_per_user=max_per_user)

    yield make
    held.audio.release_all()
    for pool in pools:
        pool.shutdown(wait=True)
