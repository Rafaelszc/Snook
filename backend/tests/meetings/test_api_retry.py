import logging
import sqlite3
from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.events import Event, RetryRequested
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.meetings import service
from tests.auth.helpers import Users
from tests.meetings.helpers import URL, FakeProbe, set_fields, upload

Uow = Callable[[], UnitOfWork]
UNKNOWN_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
STATE = "SELECT status, failed_stage, error_message, run_id FROM meetings WHERE id = ?"


@pytest.fixture
def meeting_id(ana: TestClient, probe: FakeProbe, clock: FakeClock) -> str:
    response = upload(ana)
    assert response.status_code == 201
    value: str = response.json()["id"]
    return value


@pytest.fixture
def retries(client: TestClient) -> list[Event]:
    received: list[Event] = []
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(RetryRequested, received.append)
    return received


def _fail(settings: Settings, meeting_id: str, stage: str) -> None:
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage=stage,
        error_message="falhou",
    )


def _state(settings: Settings, meeting_id: str) -> tuple[str, str | None, str | None, str]:
    with sqlite3.connect(settings.database_path) as conn:
        [row] = conn.execute(STATE, (meeting_id,)).fetchall()
    return row  # type: ignore[no-any-return]


def test_retry_transcription_goes_to_pending(
    ana: TestClient, settings: Settings, meeting_id: str, retries: list[Event]
) -> None:
    """`meetings` 24."""
    _fail(settings, meeting_id, "transcription")
    old_run = _state(settings, meeting_id)[3]

    response = ana.post(f"{URL}/{meeting_id}/retry")

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
    status, stage, message, run_id = _state(settings, meeting_id)
    assert (status, stage, message) == ("pending", None, None)
    assert run_id != old_run
    assert retries == [RetryRequested(meeting_id=meeting_id, run_id=run_id, stage="transcription")]


def test_retry_generation_goes_to_transcribed_and_keeps_data(
    ana: TestClient,
    settings: Settings,
    clock: FakeClock,
    uow: Uow,
    meeting_id: str,
    retries: list[Event],
) -> None:
    """`meetings` 25: Transcrição e Participantes (marca) intactos."""
    with uow() as unit:
        service.mark_participants_confirmed(unit, meeting_id, now=clock.now())
    _fail(settings, meeting_id, "generation")

    response = ana.post(f"{URL}/{meeting_id}/retry")

    assert response.status_code == 202
    body = response.json()
    assert (body["status"], body["failed_stage"], body["error_message"]) == (
        "transcribed",
        None,
        None,
    )
    assert body["participants_confirmed"] is True
    status, stage, message, run_id = _state(settings, meeting_id)
    assert (status, stage, message) == ("transcribed", None, None)
    assert retries == [RetryRequested(meeting_id=meeting_id, run_id=run_id, stage="generation")]


@pytest.mark.parametrize(
    "status", ["pending", "processing", "transcribed", "needs_split", "generating", "done"]
)
def test_retry_outside_failed_is_409_and_changes_nothing(
    ana: TestClient, settings: Settings, meeting_id: str, retries: list[Event], status: str
) -> None:
    """`meetings` 26."""
    set_fields(settings.database_path, meeting_id, status=status)
    before = _state(settings, meeting_id)

    response = ana.post(f"{URL}/{meeting_id}/retry")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_failed"
    assert _state(settings, meeting_id) == before
    assert retries == []


def test_retry_keeps_original_file(
    ana: TestClient, settings: Settings, probe: FakeProbe, meeting_id: str
) -> None:
    """`meetings` 27: sem novo envio; o original não muda."""
    original = settings.audio_root / meeting_id / "original.mp3"
    content = original.read_bytes()
    _fail(settings, meeting_id, "transcription")

    assert ana.post(f"{URL}/{meeting_id}/retry").status_code == 202

    assert original.read_bytes() == content
    assert len(probe.paths) == 1
    assert sorted(p.name for p in (settings.audio_root / meeting_id).iterdir()) == ["original.mp3"]


def test_retry_other_users_meeting_is_404_and_intact(
    users: Users,
    client: TestClient,
    probe: FakeProbe,
    settings: Settings,
    retries: list[Event],
) -> None:
    """`meetings` 31; SEC-02."""
    users.use("bia")
    bias = upload(client).json()["id"]
    _fail(settings, bias, "transcription")
    before = _state(settings, bias)
    users.use("ana")

    response = client.post(f"{URL}/{bias}/retry")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert _state(settings, bias) == before
    assert retries == []


def test_retry_unknown_or_forged_id_is_404(ana: TestClient, users: Users) -> None:
    assert ana.post(f"{URL}/{UNKNOWN_ID}/retry").status_code == 404
    assert ana.post(f"{URL}/..%2Fx/retry").status_code == 404


def test_retry_without_session_is_401(client: TestClient) -> None:
    """SEC-01."""
    assert client.post(f"{URL}/{UNKNOWN_ID}/retry").status_code == 401


def test_retry_with_bad_origin_is_403(
    ana: TestClient, settings: Settings, meeting_id: str, retries: list[Event]
) -> None:
    """SEC-04."""
    _fail(settings, meeting_id, "transcription")
    before = _state(settings, meeting_id)

    response = ana.post(f"{URL}/{meeting_id}/retry", headers={"Origin": "http://evil.example"})

    assert response.status_code == 403
    assert _state(settings, meeting_id) == before
    assert retries == []


def test_retry_is_logged(
    ana: TestClient, settings: Settings, meeting_id: str, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20: `meeting.retry` com `user_id` e `meeting_id`."""
    _fail(settings, meeting_id, "generation")
    caplog.set_level(logging.DEBUG)

    ana.post(f"{URL}/{meeting_id}/retry")

    [event] = [r for r in caplog.records if r.getMessage() == "meeting.retry"]
    assert event.meeting_id == meeting_id
    assert event.user_id
    assert event.stage == "generation"
