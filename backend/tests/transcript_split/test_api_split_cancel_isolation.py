from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.events import Event
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.transcript_split import service
from tests.auth.helpers import Users, rows
from tests.meetings.helpers import set_fields
from tests.participants.conftest import activate_provider
from tests.transcript_split.helpers import LineEstimate, segment_ids, split_url, waiting_split

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
BACKLOG = "2026-10-23T12:00:00Z"
ROUTES = [("GET", ""), ("PUT", ""), ("POST", "/refresh"), ("POST", "/cancel")]


def _two_parts(sizes: list[int]) -> int:
    return sizes[0] + sizes[1]


def _database(settings: Settings) -> list[Any]:
    return [
        rows(settings.database_path, "SELECT * FROM meetings"),
        rows(settings.database_path, "SELECT * FROM transcript_parts"),
    ]


def _body(settings: Settings, meeting_id: str, method: str) -> dict[str, Any] | None:
    return {"cuts": [segment_ids(settings, meeting_id)[1]]} if method == "PUT" else None


@pytest.mark.parametrize("reason", ["too_long", "adjust"])
def test_cancel_with_backlog_goes_to_done_unchanged(
    split: TestClient, settings: Settings, uow: Uow, ready: list[Event], reason: str
) -> None:
    """`transcript-split` 39: `done`, Partes iguais, sem aviso, qualquer `split_reason`."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts, split_reason=reason)
    with uow() as unit:
        snapshot = service.owner_provider(unit, meeting_id)
        service.save_parts(unit, snapshot, meeting_id, [(0, 1), (2, 2)], estimate=LineEstimate())
    set_fields(settings.database_path, meeting_id, backlog_saved_at=BACKLOG)
    parts = rows(settings.database_path, "SELECT * FROM transcript_parts")

    response = split.post(split_url(meeting_id, "/cancel"))

    assert response.status_code == 200
    assert response.json() == {"status": "done"}
    assert rows(settings.database_path, "SELECT status FROM meetings") == [("done",)]
    assert rows(settings.database_path, "SELECT * FROM transcript_parts") == parts
    assert ready == []


@pytest.mark.parametrize(
    ("status", "backlog"), [("needs_split", None), ("done", BACKLOG), ("transcribed", None)]
)
def test_cancel_outside_needs_split_or_without_backlog_is_409(
    split: TestClient, settings: Settings, uow: Uow, status: str, backlog: str | None
) -> None:
    """`transcript-split` 40."""
    meeting_id, _ = waiting_split(split, settings, uow, _two_parts)
    set_fields(settings.database_path, meeting_id, status=status, backlog_saved_at=backlog)
    before = _database(settings)

    response = split.post(split_url(meeting_id, "/cancel"))

    assert response.status_code == 409
    assert _database(settings) == before


@pytest.mark.parametrize(("method", "action"), ROUTES)
def test_other_users_meeting_is_404_and_unchanged(
    split: TestClient,
    settings: Settings,
    uow: Uow,
    users: Users,
    ready: list[Event],
    method: str,
    action: str,
) -> None:
    """`transcript-split` 28; SEC-02."""
    meeting_id, _ = waiting_split(split, settings, uow, sum)
    set_fields(settings.database_path, meeting_id, backlog_saved_at=BACKLOG)
    body = _body(settings, meeting_id, method)
    activate_provider(settings, "bia")
    users.use("bia")
    before = _database(settings)

    response = split.request(method, split_url(meeting_id, action), json=body)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert _database(settings) == before
    assert ready == []


@pytest.mark.parametrize(("method", "action"), ROUTES)
def test_without_session_is_401(client: TestClient, method: str, action: str) -> None:
    """`transcript-split` 29; SEC-01."""
    meeting_id = "00000000-0000-0000-0000-000000000000"
    body = {"cuts": [1]} if method == "PUT" else None

    response = client.request(method, split_url(meeting_id, action), json=body)

    assert response.status_code == 401


@pytest.mark.parametrize(("method", "action"), ROUTES[1:])
def test_write_without_valid_origin_is_403(
    split: TestClient, settings: Settings, uow: Uow, method: str, action: str
) -> None:
    """SEC-04: `PUT`, `refresh` e `cancel` mudam estado."""
    meeting_id, _ = waiting_split(split, settings, uow, sum)
    set_fields(settings.database_path, meeting_id, backlog_saved_at=BACKLOG)
    body = _body(settings, meeting_id, method)
    before = _database(settings)

    response = split.request(
        method, split_url(meeting_id, action), json=body, headers={"Origin": "http://evil.example"}
    )

    assert response.status_code == 403
    assert _database(settings) == before
