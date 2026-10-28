from collections.abc import Callable
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.events import Event, ParticipantsConfirmed, RetryRequested
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import messages, service
from tests.auth.helpers import rows
from tests.meetings.helpers import set_fields
from tests.transcript_split.helpers import FakeEstimate, confirmed

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
STATE = "SELECT status, failed_stage, error_message, run_id FROM meetings"


def _state(settings: Settings) -> tuple[Any, ...]:
    [row] = rows(settings.database_path, STATE)
    return tuple(row)


def _consume(client: TestClient, uow: Uow, event: Event, estimate: Any = None) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    service.on_generation_requested(
        event, uow, now=app.state.clock.now, estimate=estimate or FakeEstimate()
    )


def _events(meeting_id: str, run_id: str) -> list[Event]:
    return [
        ParticipantsConfirmed(meeting_id=meeting_id, run_id=run_id),
        RetryRequested(meeting_id=meeting_id, run_id=run_id, stage="generation"),
    ]


@pytest.mark.parametrize("kind", [0, 1], ids=["confirmed", "retry"])
def test_event_in_transcribed_prepares_once(
    idle: TestClient, settings: Settings, uow: Uow, ready: list[Event], kind: int
) -> None:
    meeting_id = confirmed(idle, settings)

    _consume(idle, uow, _events(meeting_id, _state(settings)[3])[kind])

    assert _state(settings)[0] == "generating"
    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(1,)]
    assert len(ready) == 1


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "needs_split", "split_reason": "too_long"},
        {"status": "generating"},
        {"status": "done", "backlog_saved_at": "2026-10-28T12:00:00Z"},
        {"status": "failed", "failed_stage": "generation", "error_message": "falhou"},
    ],
    ids=["needs_split", "generating", "done", "failed"],
)
@pytest.mark.parametrize("kind", [0, 1], ids=["confirmed", "retry"])
def test_event_outside_transcribed_is_ignored(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    ready: list[Event],
    fields: dict[str, str],
    kind: int,
) -> None:
    """`transcript-split` 46."""
    meeting_id = confirmed(idle, settings)
    set_fields(settings.database_path, meeting_id, **fields)
    before = rows(settings.database_path, "SELECT * FROM meetings")
    estimate = FakeEstimate()

    _consume(idle, uow, _events(meeting_id, _state(settings)[3])[kind], estimate)

    assert rows(settings.database_path, "SELECT * FROM meetings") == before
    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(0,)]
    assert estimate.calls == []
    assert ready == []


@pytest.mark.parametrize("kind", [0, 1], ids=["confirmed", "retry"])
def test_event_with_old_run_id_is_ignored(
    idle: TestClient, settings: Settings, uow: Uow, ready: list[Event], kind: int
) -> None:
    """ADR-0007."""
    meeting_id = confirmed(idle, settings)
    before = _state(settings)

    _consume(idle, uow, _events(meeting_id, "outro-run")[kind])

    assert _state(settings) == before
    assert ready == []


def test_retry_of_transcription_is_ignored(
    idle: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    meeting_id = confirmed(idle, settings)
    before = _state(settings)

    _consume(
        idle, uow, RetryRequested(meeting_id=meeting_id, run_id=before[3], stage="transcription")
    )

    assert _state(settings) == before
    assert ready == []


def test_consumer_exception_goes_to_failed(
    idle: TestClient, settings: Settings, uow: Uow, ready: list[Event]
) -> None:
    """SEC-19: exceção não deixa a Reunião presa em `transcribed`."""
    meeting_id = confirmed(idle, settings)

    def broken(provider: str, model: str, text: str) -> int:
        raise RuntimeError("falhou")

    _consume(idle, uow, _events(meeting_id, _state(settings)[3])[0], broken)

    assert _state(settings)[:3] == ("failed", "generation", messages.UNEXPECTED)
    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(0,)]
    assert ready == []


def test_app_consumes_confirmation(ana: TestClient, settings: Settings) -> None:
    """Assinatura real: confirmar os nomes leva a Reunião pequena a `generating`."""
    app: FastAPI = ana.app  # type: ignore[assignment]
    app.state.transcription.stop()

    meeting_id = confirmed(ana, settings)

    assert ana.get(f"/api/meetings/{meeting_id}").json()["status"] == "generating"
    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(1,)]
