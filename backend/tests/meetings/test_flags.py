from collections.abc import Callable
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.main import create_app
from snook.modules.meetings import service
from tests.auth.helpers import Users, rows
from tests.conftest import InertTranscription
from tests.meetings.helpers import URL, FakeProbe, set_fields, upload

Uow = Callable[[], UnitOfWork]
UNKNOWN_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"


@pytest.fixture
def meeting_id(ana: TestClient, probe: FakeProbe, clock: FakeClock) -> str:
    response = upload(ana)
    assert response.status_code == 201
    value: str = response.json()["id"]
    return value


def _mark_both(uow: Uow, meeting_id: str, clock: FakeClock) -> None:
    with uow() as unit:
        service.mark_participants_confirmed(unit, meeting_id, now=clock.now())
        service.mark_backlog_saved(unit, meeting_id, now=clock.now())


def _flags(uow: Uow, meeting_id: str) -> service.MeetingFlags:
    with uow() as unit:
        return service.read_flags(unit, meeting_id)


def _detail_flags(client: TestClient, meeting_id: str) -> tuple[bool, bool]:
    body = client.get(f"{URL}/{meeting_id}").json()
    return body["participants_confirmed"], body["has_backlog"]


def test_new_meeting_has_no_flags(ana: TestClient, uow: Uow, meeting_id: str) -> None:
    assert _flags(uow, meeting_id) == service.MeetingFlags(
        participants_confirmed=False, has_backlog=False
    )
    assert _detail_flags(ana, meeting_id) == (False, False)


def test_both_marks_are_read_and_shown_in_detail(
    ana: TestClient, uow: Uow, clock: FakeClock, meeting_id: str
) -> None:
    _mark_both(uow, meeting_id, clock)

    assert _flags(uow, meeting_id) == service.MeetingFlags(
        participants_confirmed=True, has_backlog=True
    )
    assert _detail_flags(ana, meeting_id) == (True, True)


def test_marks_join_the_caller_transaction(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    with pytest.raises(RuntimeError), uow() as unit:
        service.mark_participants_confirmed(unit, meeting_id, now=clock.now())
        service.mark_backlog_saved(unit, meeting_id, now=clock.now())
        raise RuntimeError("falha de quem chama")

    assert rows(
        settings.database_path, "SELECT participants_confirmed_at, backlog_saved_at FROM meetings"
    ) == [(None, None)]


def test_mark_keeps_first_timestamp(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    first = clock.now()
    _mark_both(uow, meeting_id, clock)
    clock.advance(timedelta(hours=1))
    _mark_both(uow, meeting_id, clock)

    stamp = first.strftime("%Y-%m-%dT%H:%M:%SZ")
    assert rows(
        settings.database_path, "SELECT participants_confirmed_at, backlog_saved_at FROM meetings"
    ) == [(stamp, stamp)]


def test_marks_survive_retry(
    ana: TestClient, uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    _mark_both(uow, meeting_id, clock)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="falhou",
    )

    with uow() as unit:
        service.update_status(unit, meeting_id, "transcribed", now=clock.now())

    assert _detail_flags(ana, meeting_id) == (True, True)


def test_marks_survive_regeneration(
    ana: TestClient, uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    _mark_both(uow, meeting_id, clock)
    set_fields(settings.database_path, meeting_id, status="done")

    with uow() as unit:
        service.update_status(unit, meeting_id, "generating", now=clock.now())
    with uow() as unit:
        service.update_status(unit, meeting_id, "done", now=clock.now())

    assert _detail_flags(ana, meeting_id) == (True, True)


def _running(settings: Settings) -> tuple[FastAPI, TestClient]:
    app = create_app(settings)
    app.state.transcription = InertTranscription()
    app.state.media_probe = FakeProbe()
    client = TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"}
    )
    return app, client


def test_marks_survive_restart(settings: Settings) -> None:
    clock = FakeClock(datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    first, client = _running(settings)
    first.state.clock = clock
    with client:
        Users(client).add("ana")
        meeting_id = upload(client).json()["id"]
        with UnitOfWork(first.state.session_factory, first.state.event_bus.publish) as unit:
            service.mark_participants_confirmed(unit, meeting_id, now=clock.now())
            service.mark_backlog_saved(unit, meeting_id, now=clock.now())
        session = client.cookies["snook_session"]

    second, client = _running(settings)
    second.state.clock = clock
    with client:
        client.cookies.set("snook_session", session)
        assert _detail_flags(client, meeting_id) == (True, True)
        with UnitOfWork(second.state.session_factory, second.state.event_bus.publish) as unit:
            flags = service.read_flags(unit, meeting_id)

    assert flags == service.MeetingFlags(participants_confirmed=True, has_backlog=True)


def test_marks_on_missing_meeting_are_reported(uow: Uow, clock: FakeClock) -> None:
    with pytest.raises(service.MeetingGone), uow() as unit:
        service.mark_participants_confirmed(unit, UNKNOWN_ID, now=clock.now())
    with pytest.raises(service.MeetingGone), uow() as unit:
        service.mark_backlog_saved(unit, UNKNOWN_ID, now=clock.now())
    with pytest.raises(service.MeetingGone), uow() as unit:
        service.read_flags(unit, UNKNOWN_ID)
