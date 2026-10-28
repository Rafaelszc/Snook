from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import FakeGenerate, story
from tests.backlog_review.helpers import (
    NOT_DONE,
    backlog_url,
    leave_done,
    stories,
    stories_url,
    with_backlog,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]

FIELDS = {
    "name": "Cadastrar fornecedor",
    "as_a": "comprador",
    "i_want": "cadastrar fornecedor com CNPJ",
    "so_that": "eu possa emitir pedidos de compra",
    "priority": "Low",
    "story_points": 8,
}


def _meeting(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(
        client,
        settings,
        uow,
        generate,
        ("Cadastro", [story("Cadastrar cliente"), story("Editar cliente")]),
    )


def _patch(client: TestClient, meeting_id: str, body: dict[str, Any]) -> Any:
    story_id = stories(client, meeting_id)["US-01"]["id"]
    return client.patch(stories_url(meeting_id, story_id), json=body)


def test_patch_saves_fields_and_keeps_us_id(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 11."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = stories(idle, meeting_id)

    response = _patch(idle, meeting_id, {**FIELDS, "name": "  Cadastrar fornecedor  "})

    assert response.status_code == 200
    body = response.json()
    assert {key: body[key] for key in FIELDS} == FIELDS
    assert body["us_id"] == "US-01"
    assert body["id"] == before["US-01"]["id"]
    after = stories(idle, meeting_id)
    assert {key: after["US-01"][key] for key in FIELDS} == FIELDS
    assert after["US-01"]["acceptance_criteria"] == before["US-01"]["acceptance_criteria"]
    assert after["US-02"] == before["US-02"]


def test_patch_changes_only_sent_fields(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 11."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = stories(idle, meeting_id)["US-01"]

    response = _patch(idle, meeting_id, {"story_points": 13})

    assert response.status_code == 200
    assert stories(idle, meeting_id)["US-01"] == {**before, "story_points": 13}


@pytest.mark.parametrize(
    "body",
    [
        {"priority": "Urgent"},
        {"priority": "high"},
        {"priority": None},
        {"story_points": 4},
        {"story_points": 0},
        {"story_points": "5"},
        {"story_points": True},
    ],
)
def test_invalid_priority_or_points_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, body: dict[str, Any]
) -> None:
    """`backlog-review` 12: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _patch(idle, meeting_id, body)

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == list(body)
    assert idle.get(backlog_url(meeting_id)).json() == before


@pytest.mark.parametrize("field", ["name", "as_a", "i_want", "so_that"])
@pytest.mark.parametrize("value", ["", "   ", None])
def test_empty_text_is_422(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    field: str,
    value: str | None,
) -> None:
    """`backlog-review` 13."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _patch(idle, meeting_id, {field: value})

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == [field]
    assert idle.get(backlog_url(meeting_id)).json() == before


@pytest.mark.parametrize(
    ("field", "size"), [("name", 201), ("as_a", 2001), ("i_want", 2001), ("so_that", 2001)]
)
def test_text_above_max_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, field: str, size: int
) -> None:
    """SEC-09: nome até 200; `as_a`, `i_want`, `so_that` até 2000."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _patch(idle, meeting_id, {field: "x" * size})

    assert response.status_code == 422
    assert _patch(idle, meeting_id, {field: "x" * (size - 1)}).status_code == 200


def test_unknown_field_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-09: `us_id` não é editável."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _patch(idle, meeting_id, {"us_id": "US-09"})

    assert response.status_code == 422


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()["epics"]
    story_id = stories(idle, meeting_id)["US-01"]["id"]
    leave_done(settings, meeting_id, status)

    response = idle.patch(stories_url(meeting_id, story_id), json=FIELDS)

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert idle.get(backlog_url(meeting_id)).json()["epics"] == before


def test_story_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02."""
    first = _meeting(idle, settings, uow, generate)
    second = _meeting(idle, settings, uow, generate)
    before = stories(idle, second)

    response = idle.patch(stories_url(first, before["US-01"]["id"]), json=FIELDS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "story_not_found"
    assert stories(idle, second) == before


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = stories(idle, meeting_id)
    users.use("bia")

    response = idle.patch(stories_url(meeting_id, before["US-01"]["id"]), json=FIELDS)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    users.use("ana")
    assert stories(idle, meeting_id) == before


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.patch(stories_url("00000000-0000-0000-0000-000000000000", 1), json={})

    assert response.status_code == 401
