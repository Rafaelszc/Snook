import logging
from collections.abc import Callable
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock, SystemClock
from snook.core.settings import Settings
from snook.modules.diarized_transcription.dispatcher import TranscriptionDispatcher
from snook.modules.diarized_transcription.engines.fakes import FakeEngines, fake_engines
from tests.auth.helpers import Users
from tests.diarized_transcription.conftest import wait_for
from tests.diarized_transcription.helpers import create, state

pytestmark = pytest.mark.usefixtures("probe")

Make = Callable[..., TranscriptionDispatcher]


def _upload(client: TestClient, clock: FakeClock) -> str:
    clock.advance(timedelta(seconds=1))  # ordem de criação sem empate
    return create(client)


def _status(settings: Settings, meeting_id: str) -> str:
    return str(state(settings.database_path, meeting_id)[0])


def _statuses(settings: Settings, ids: list[str]) -> list[str]:
    return [_status(settings, meeting_id) for meeting_id in ids]


def _finish(held: FakeEngines, settings: Settings, meeting_id: str) -> None:
    held.audio.release(meeting_id)
    wait_for(lambda: _status(settings, meeting_id) == "transcribed")


@pytest.mark.parametrize(("limit", "workers"), [(1, 2), (2, 3)])
def test_user_never_has_more_than_limit_processing(
    ana: TestClient,
    settings: Settings,
    clock: FakeClock,
    held: FakeEngines,
    threaded: Make,
    limit: int,
    workers: int,
) -> None:
    """`diarized-transcription` 28."""
    dispatcher = threaded(workers=workers, max_per_user=limit)
    ids = [_upload(ana, clock) for _ in range(limit + 2)]
    for meeting_id in ids[:limit]:
        assert held.audio.wait_started(meeting_id)

    assert _statuses(settings, ids) == ["processing"] * limit + ["pending"] * 2
    assert dispatcher.running == limit
    assert not any(held.audio.started(meeting_id) for meeting_id in ids[limit:])


def test_waiting_meeting_starts_when_one_leaves_in_creation_order(
    ana: TestClient, settings: Settings, clock: FakeClock, held: FakeEngines, threaded: Make
) -> None:
    """`diarized-transcription` 29: sem recusa; espera em `pending` e segue a ordem."""
    threaded(workers=2, max_per_user=1)
    first, second, third = (_upload(ana, clock) for _ in range(3))
    assert held.audio.wait_started(first)
    assert _statuses(settings, [second, third]) == ["pending", "pending"]

    _finish(held, settings, first)

    assert held.audio.wait_started(second)
    assert _statuses(settings, [first, second, third]) == ["transcribed", "processing", "pending"]

    _finish(held, settings, second)

    assert held.audio.wait_started(third)
    _finish(held, settings, third)


def test_limit_of_one_user_does_not_delay_another(
    users: Users,
    client: TestClient,
    settings: Settings,
    clock: FakeClock,
    held: FakeEngines,
    threaded: Make,
) -> None:
    """`diarized-transcription` 30: `TRANSCRIPTION_WORKERS` 2 e `TRANSCRIPTION_MAX_PER_USER` 1."""
    threaded(workers=2, max_per_user=1)
    users.use("ana")
    ana_first = _upload(client, clock)
    ana_second = _upload(client, clock)
    users.use("bia")
    bia_first = _upload(client, clock)

    assert held.audio.wait_started(ana_first)
    assert held.audio.wait_started(bia_first)
    assert _statuses(settings, [ana_first, ana_second, bia_first]) == [
        "processing",
        "pending",
        "processing",
    ]


def test_global_capacity_caps_all_users(
    users: Users,
    client: TestClient,
    settings: Settings,
    clock: FakeClock,
    held: FakeEngines,
    threaded: Make,
) -> None:
    """ADR-0010: com 1 worker, Bia espera Ana mesmo abaixo do próprio limite."""
    threaded(workers=1, max_per_user=1)
    users.use("ana")
    ana_first = _upload(client, clock)
    users.use("bia")
    bia_first = _upload(client, clock)
    assert held.audio.wait_started(ana_first)
    assert _status(settings, bia_first) == "pending"

    _finish(held, settings, ana_first)

    assert held.audio.wait_started(bia_first)


def test_isolation_off_is_logged(caplog: pytest.LogCaptureFixture, tmp_path: Path) -> None:
    """ADR-0010: `TRANSCRIPTION_WORKERS` <= `TRANSCRIPTION_MAX_PER_USER` sobe com aviso no log."""
    caplog.set_level(logging.WARNING)
    TranscriptionDispatcher(
        engines=fake_engines(),
        workers=1,
        max_per_user=1,
        audio_root=tmp_path,
        now=SystemClock().now,
    )
    assert "transcription.isolation_off" in caplog.text
