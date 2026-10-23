from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.meetings import service
from tests.auth.helpers import rows
from tests.meetings.helpers import URL, FakeProbe, set_fields, upload

Uow = Callable[[], UnitOfWork]

# Tabela de transições de `01-prd/meetings.md`: (de, para, etapa do `failed`, troca `run_id`).
ALLOWED = [
    ("pending", "processing", None, False),
    ("processing", "transcribed", None, False),
    ("processing", "failed", "transcription", False),
    ("transcribed", "generating", None, True),
    ("transcribed", "needs_split", None, False),
    ("transcribed", "failed", "generation", False),
    ("needs_split", "generating", None, True),
    ("needs_split", "failed", "generation", False),
    ("generating", "done", None, False),
    ("generating", "failed", "generation", False),
    ("done", "generating", None, True),
    ("done", "needs_split", None, False),
    ("done", "failed", "generation", False),
]

REFUSED = [
    ("pending", "transcribed", None),
    ("pending", "failed", "transcription"),
    ("processing", "pending", None),
    ("processing", "failed", "generation"),
    ("transcribed", "failed", "transcription"),
    ("transcribed", "done", None),
    ("generating", "needs_split", None),
    ("done", "pending", None),
    ("failed", "done", None),
    ("failed", "failed", "generation"),
    ("needs_split", "done", None),  # sem backlog gravado
]


@pytest.fixture
def meeting_id(ana: TestClient, probe: FakeProbe, clock: FakeClock) -> str:
    response = upload(ana)
    assert response.status_code == 201
    value: str = response.json()["id"]
    return value


def _db(settings: Settings) -> Path:
    return settings.database_path


def _stored(settings: Settings, meeting_id: str) -> tuple[object, ...]:
    found = rows(
        _db(settings), "SELECT id, status, failed_stage, error_message, run_id FROM meetings"
    )
    return next(tuple(row[1:]) for row in found if row[0] == meeting_id)


def _put(settings: Settings, meeting_id: str, status: str) -> None:
    stage = "generation" if status == "failed" else None
    message = "falhou" if status == "failed" else None
    set_fields(_db(settings), meeting_id, status=status, failed_stage=stage, error_message=message)


@pytest.mark.parametrize(("source", "target", "stage", "new_run"), ALLOWED)
def test_allowed_transition_is_saved_and_shown_in_detail(
    ana: TestClient,
    uow: Uow,
    settings: Settings,
    clock: FakeClock,
    meeting_id: str,
    source: str,
    target: str,
    stage: str | None,
    new_run: bool,
) -> None:
    _put(settings, meeting_id, source)
    old_run = _stored(settings, meeting_id)[3]
    message = "erro na etapa" if stage else None

    with uow() as unit:
        run_id = service.update_status(
            unit, meeting_id, target, failed_stage=stage, message=message, now=clock.now()
        )

    status, saved_stage, saved_message, saved_run = _stored(settings, meeting_id)
    assert (status, saved_stage, saved_message) == (target, stage, message)
    assert saved_run == run_id
    assert (saved_run != old_run) is new_run
    detail = ana.get(f"{URL}/{meeting_id}").json()
    assert detail["status"] == target
    assert detail["failed_stage"] == stage
    assert detail["error_message"] == message


@pytest.mark.parametrize(
    ("stage", "target"), [("transcription", "pending"), ("generation", "transcribed")]
)
def test_leaving_failed_clears_failure_and_changes_run_id(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str, stage: str, target: str
) -> None:
    set_fields(
        _db(settings), meeting_id, status="failed", failed_stage=stage, error_message="falhou"
    )
    old_run = _stored(settings, meeting_id)[3]

    with uow() as unit:
        service.update_status(unit, meeting_id, target, now=clock.now())

    status, saved_stage, saved_message, saved_run = _stored(settings, meeting_id)
    assert (status, saved_stage, saved_message) == (target, None, None)
    assert saved_run != old_run


@pytest.mark.parametrize(
    ("stage", "target"), [("transcription", "transcribed"), ("generation", "pending")]
)
def test_leaving_failed_follows_the_failed_stage(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str, stage: str, target: str
) -> None:
    set_fields(
        _db(settings), meeting_id, status="failed", failed_stage=stage, error_message="falhou"
    )
    before = _stored(settings, meeting_id)

    with pytest.raises(service.InvalidStatusUpdate), uow() as unit:
        service.update_status(unit, meeting_id, target, now=clock.now())

    assert _stored(settings, meeting_id) == before


def test_needs_split_goes_to_done_only_with_backlog(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    set_fields(
        _db(settings), meeting_id, status="needs_split", backlog_saved_at="2026-10-23T12:00:00Z"
    )
    old_run = _stored(settings, meeting_id)[3]

    with uow() as unit:
        service.update_status(unit, meeting_id, "done", now=clock.now())

    assert _stored(settings, meeting_id) == ("done", None, None, old_run)


@pytest.mark.parametrize(("source", "target", "stage"), REFUSED)
def test_transition_outside_table_is_refused_and_status_kept(
    uow: Uow,
    settings: Settings,
    clock: FakeClock,
    meeting_id: str,
    source: str,
    target: str,
    stage: str | None,
) -> None:
    _put(settings, meeting_id, source)
    before = _stored(settings, meeting_id)

    with pytest.raises(service.InvalidStatusUpdate), uow() as unit:
        service.update_status(
            unit,
            meeting_id,
            target,
            failed_stage=stage,
            message="falhou" if stage else None,
            now=clock.now(),
        )

    assert _stored(settings, meeting_id) == before


@pytest.mark.parametrize("target", ["deleted", "PENDING", "", "queued"])
def test_status_outside_list_is_refused(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str, target: str
) -> None:
    before = _stored(settings, meeting_id)

    with pytest.raises(service.InvalidStatusUpdate), uow() as unit:
        service.update_status(unit, meeting_id, target, now=clock.now())

    assert _stored(settings, meeting_id) == before


@pytest.mark.parametrize(
    ("stage", "message"),
    [(None, "falhou"), ("transcription", None), ("transcription", "   "), ("parsing", "falhou")],
)
def test_failed_needs_valid_stage_and_message(
    uow: Uow,
    settings: Settings,
    clock: FakeClock,
    meeting_id: str,
    stage: str | None,
    message: str | None,
) -> None:
    _put(settings, meeting_id, "processing")
    before = _stored(settings, meeting_id)

    with pytest.raises(service.InvalidStatusUpdate), uow() as unit:
        service.update_status(
            unit, meeting_id, "failed", failed_stage=stage, message=message, now=clock.now()
        )

    assert _stored(settings, meeting_id) == before


def test_stage_or_message_outside_failed_is_refused(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    before = _stored(settings, meeting_id)

    with pytest.raises(service.InvalidStatusUpdate), uow() as unit:
        service.update_status(
            unit, meeting_id, "processing", failed_stage="transcription", now=clock.now()
        )

    assert _stored(settings, meeting_id) == before


def test_missing_meeting_is_reported(uow: Uow, clock: FakeClock) -> None:
    with pytest.raises(service.MeetingGone), uow() as unit:
        service.update_status(
            unit, "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f", "processing", now=clock.now()
        )


def test_current_run_helper_ignores_stale_run_id(
    uow: Uow, settings: Settings, clock: FakeClock, meeting_id: str
) -> None:
    created_run = str(_stored(settings, meeting_id)[3])
    _put(settings, meeting_id, "transcribed")

    with uow() as unit:
        new_run = service.update_status(unit, meeting_id, "generating", now=clock.now())

    with uow() as unit:
        assert service.is_current_run(unit, meeting_id, new_run)
        assert service.is_current_run(unit, meeting_id, new_run, status="generating")
        assert not service.is_current_run(unit, meeting_id, new_run, status="transcribed")
        assert not service.is_current_run(unit, meeting_id, created_run)
        assert not service.is_current_run(unit, "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f", new_run)
