"""Corridas e falhas do dispatcher: exclusão, upload, banco, pool quebrado e parada."""

import inspect
import sqlite3
import time
from collections.abc import Callable
from concurrent.futures import BrokenExecutor, Executor, Future
from concurrent.futures.process import BrokenProcessPool
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core import files
from snook.core.clock import FakeClock
from snook.core.events import MeetingCreated
from snook.core.settings import Settings
from snook.main import create_app
from snook.modules.diarized_transcription import dispatcher as dispatcher_module
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.dispatcher import (
    TranscriptionDispatcher,
    process_pool,
    terminate_workers,
)
from snook.modules.diarized_transcription.engines.fakes import FakeEngines, SyncExecutor
from snook.modules.meetings import service as meetings_service
from tests.auth.helpers import rows
from tests.diarized_transcription.conftest import install, wait_for
from tests.diarized_transcription.helpers import create, segments, state
from tests.meetings.helpers import set_fields

pytestmark = pytest.mark.usefixtures("probe", "clock")


def _status(settings: Settings, meeting_id: str) -> str:
    return str(state(settings.database_path, meeting_id)[0])


def _app(client: TestClient) -> FastAPI:
    app: FastAPI = client.app  # type: ignore[assignment]
    return app


def _delete_row(settings: Settings, meeting_id: str) -> None:
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM meetings WHERE id = ?", (meeting_id,))


def test_meeting_without_original_yet_is_not_claimed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher, engines: FakeEngines
) -> None:
    """Upload commitado, original ainda em `.tmp`: espera o `MeetingCreated` do fim do move."""
    meeting_id = create(ana)
    original = settings.audio_root / meeting_id / "original.mp3"
    hidden = original.with_name("escondido.mp3")
    original.rename(hidden)
    set_fields(settings.database_path, meeting_id, status="pending")

    dispatcher.wake()

    assert _status(settings, meeting_id) == "pending"
    assert len(engines.audio.sources) == 1

    hidden.rename(original)
    [(run_id,)] = rows(settings.database_path, "SELECT run_id FROM meetings")
    _app(ana).state.event_bus.publish(MeetingCreated(meeting_id=meeting_id, run_id=run_id))

    assert _status(settings, meeting_id) == "transcribed"


def test_unsafe_path_does_not_block_queue(
    ana: TestClient,
    settings: Settings,
    clock: FakeClock,
    dispatcher: TranscriptionDispatcher,
    tmp_path: Path,
) -> None:
    """SEC-15: diretório trocado por link é pulado; a Reunião seguinte transcreve."""
    blocked = create(ana)
    target = settings.audio_root / blocked
    outside = tmp_path / "fora"
    target.rename(outside)
    target.symlink_to(outside)
    set_fields(settings.database_path, blocked, status="pending")
    clock.advance(timedelta(seconds=1))  # a bloqueada é a mais antiga da fila

    other = create(ana)

    assert _status(settings, blocked) == "pending"
    assert _status(settings, other) == "transcribed"


def test_delete_just_before_move_does_not_recreate_dir(
    ana: TestClient,
    settings: Settings,
    dispatcher: TranscriptionDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`diarized-transcription` 17: exclusão entre o commit e o move."""
    move = files.move_into_meeting_dir

    def delete_then_move(root: Path, source: Path, meeting_id: str, *args: Any, **kw: Any) -> Path:
        if "treated" in str(args):
            _delete_row(settings, meeting_id)
            files.remove_meeting_dir(root, meeting_id)
        return move(root, source, meeting_id, *args, **kw)

    monkeypatch.setattr(dispatcher_module.files, "move_into_meeting_dir", delete_then_move)

    meeting_id = create(ana)

    assert not (settings.audio_root / meeting_id).exists()
    assert list((settings.audio_root / ".tmp").iterdir()) == []


def test_delete_just_after_move_removes_leftover(
    ana: TestClient,
    settings: Settings,
    dispatcher: TranscriptionDispatcher,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exclusão logo depois do move: o diretório que sobrou é apagado (SEC-24)."""
    move = files.move_into_meeting_dir

    def move_then_delete(root: Path, source: Path, meeting_id: str, *args: Any, **kw: Any) -> Path:
        moved = move(root, source, meeting_id, *args, **kw)
        if "treated" in str(args):
            _delete_row(settings, meeting_id)  # `rmtree` da exclusão ainda não rodou
        return moved

    monkeypatch.setattr(dispatcher_module.files, "move_into_meeting_dir", move_then_delete)

    meeting_id = create(ana)

    assert not (settings.audio_root / meeting_id).exists()


def test_claim_failure_retries_and_queue_moves_on(
    ana: TestClient,
    settings: Settings,
    engines: FakeEngines,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-19: erro passageiro do banco na escolha não para a fila."""
    dispatcher = TranscriptionDispatcher(
        engines=engines,
        workers=2,
        max_per_user=1,
        audio_root=settings.audio_root,
        now=lambda: _app(ana).state.clock.now(),
        executor_factory=lambda _n: SyncExecutor(),
        claim_retry_seconds=0.01,
    )
    app = _app(ana)
    app.state.transcription.stop()
    app.state.transcription = dispatcher
    dispatcher.start(app.state.session_factory, app.state.event_bus.publish)
    real = meetings_service.next_pending_for_transcription
    calls: list[int] = []

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError("database is locked")
        return real(*args, **kwargs)

    monkeypatch.setattr(dispatcher_module.meetings, "next_pending_for_transcription", flaky)

    meeting_id = create(ana)

    wait_for(lambda: _status(settings, meeting_id) == "transcribed")


class _DyingPool(Executor):
    """Primeiro trabalho perde o subprocesso; depois o pool fica quebrado, como o real."""

    def __init__(self) -> None:
        self.broken = False

    def submit(self, fn: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Future[Any]:
        if self.broken:
            raise BrokenExecutor("pool quebrado")
        self.broken = True
        future: Future[Any] = Future()
        future.set_exception(BrokenProcessPool("subprocesso morreu"))
        return future


def test_broken_pool_is_replaced_before_next_meeting(
    ana: TestClient, settings: Settings, engines: FakeEngines
) -> None:
    pools: list[Executor] = []

    def factory(_workers: int) -> Executor:
        pool: Executor = _DyingPool() if not pools else SyncExecutor()
        pools.append(pool)
        return pool

    install(ana, engines, factory, workers=2, max_per_user=1)

    first = create(ana)
    second = create(ana)

    assert state(settings.database_path, first) == ("failed", "transcription", messages.UNEXPECTED)
    assert _status(settings, second) == "transcribed"
    assert len(pools) == 2


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def test_terminate_workers_kills_running_subprocess() -> None:
    """Parada não espera a transcrição em andamento."""
    pool = process_pool(1)
    future = pool.submit(_sleep, 60)
    wait_for(lambda: future.running(), timeout=30)
    processes = list(pool._processes.values())  # type: ignore[attr-defined]

    started = time.monotonic()
    terminate_workers(pool)
    for process in processes:
        process.join(10)

    assert time.monotonic() - started < 10
    assert not any(process.is_alive() for process in processes)


def test_startup_failure_after_dispatcher_start_still_stops_it(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Falha depois do passo 6 da subida não deixa executor nem subprocesso vivo."""
    calls: list[str] = []

    class Spy:
        def start(self, *_args: object) -> None:
            calls.append("start")

        def stop(self) -> None:
            calls.append("stop")

        def on_event(self, _event: object) -> None: ...

    def broken_cleanup(_app: FastAPI) -> None:
        raise RuntimeError("banco indisponível")

    monkeypatch.setattr("snook.main._cleanup_sessions", broken_cleanup)
    app = create_app(settings)
    app.state.transcription = Spy()

    with pytest.raises(RuntimeError), TestClient(app):
        pass

    assert calls == ["start", "stop"]


def test_many_pending_with_sync_executor_do_not_recurse(
    ana: TestClient, settings: Settings, engines: FakeEngines, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Fila longa drenada num laço, sem uma chamada aninhada por Reunião."""
    ids = [create(ana) for _ in range(30)]  # dispatcher inerte: ficam em `pending`
    depth: list[int] = []
    real = dispatcher_module.run_job

    def measured(*args: Any) -> Any:
        depth.append(len(inspect.stack(0)))
        return real(*args)

    monkeypatch.setattr(dispatcher_module, "run_job", measured)
    install(ana, engines, lambda _n: SyncExecutor(), workers=2, max_per_user=1)

    assert all(_status(settings, meeting_id) == "transcribed" for meeting_id in ids)
    assert max(depth) - min(depth) <= 15
    assert len(segments(settings.database_path, ids[-1])) == 2
