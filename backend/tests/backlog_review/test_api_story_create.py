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
    epic_ids,
    epic_stories_url,
    leave_done,
    new_story,
    participant_ids,
    with_backlog,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _meeting(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(
        client,
        settings,
        uow,
        generate,
        ("Cadastro", [story("Cadastrar cliente")]),
        ("Relatórios", [story("Exportar vendas"), story("Imprimir vendas")]),
    )


def _post(client: TestClient, meeting_id: str, body: dict[str, Any]) -> Any:
    epic_id = epic_ids(client, meeting_id)["Cadastro"]
    return client.post(epic_stories_url(meeting_id, epic_id), json=body)


def test_creates_story_with_next_us_id_at_end_of_epic(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 17 (Q49)."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _post(idle, meeting_id, new_story(name="  Emitir nota "))

    assert response.status_code == 201
    body = response.json()
    assert body["us_id"] == "US-04"
    assert body["name"] == "Emitir nota"
    assert [(c["given"], c["when"], c["then"]) for c in body["acceptance_criteria"]] == [
        ("pedido pago", "emito", "nota sai")
    ]
    epics = idle.get(backlog_url(meeting_id)).json()["epics"]
    assert epics[0]["user_stories"][-1] == body
    assert [s["us_id"] for s in epics[0]["user_stories"]] == ["US-01", "US-04"]


def test_creates_in_empty_epic(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 17: Epic recém-criada, sem US."""
    meeting_id = _meeting(idle, settings, uow, generate)
    epic_id = idle.post(f"/api/meetings/{meeting_id}/epics", json={"name": "Nova"}).json()["id"]

    response = idle.post(epic_stories_url(meeting_id, epic_id), json=new_story())

    assert response.status_code == 201
    epics = idle.get(backlog_url(meeting_id)).json()["epics"]
    assert [s["us_id"] for s in epics[-1]["user_stories"]] == ["US-04"]


def test_requester_and_instant_are_optional(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 18."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _post(idle, meeting_id, new_story())

    assert response.status_code == 201
    assert response.json()["requested_by"] is None
    assert response.json()["requested_at"] is None


def test_requester_and_instant_are_saved_when_sent(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 14, 15, 18."""
    meeting_id = _meeting(idle, settings, uow, generate)
    bia = participant_ids(idle, meeting_id)["Bia"]

    response = _post(idle, meeting_id, new_story(requested_by=bia, requested_at="00:10:00"))

    assert response.status_code == 201
    assert response.json()["requested_by"] == {"id": bia, "name": "Bia"}
    assert response.json()["requested_at"] == "00:10:00"


@pytest.mark.parametrize(
    "body",
    [
        new_story(acceptance_criteria=[]),
        {key: value for key, value in new_story().items() if key != "acceptance_criteria"},
        {key: value for key, value in new_story().items() if key != "so_that"},
        new_story(name="   "),
        new_story(as_a="x" * 2001),
        new_story(name="x" * 201),
        new_story(priority="Urgent"),
        new_story(story_points=4),
        new_story(acceptance_criteria=[{"given": "a", "when": " ", "then": "c"}]),
        new_story(acceptance_criteria=[{"given": "a", "when": "b", "then": "x" * 1001}]),
        new_story(requested_at="01:06:41"),
        new_story(requested_by=999_999),
    ],
)
def test_invalid_body_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, body: dict[str, Any]
) -> None:
    """`backlog-review` 12 a 15, 17; SEC-09: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _post(idle, meeting_id, body)

    assert response.status_code == 422
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_rejected_create_does_not_spend_us_number(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 17: recusa não reserva número."""
    meeting_id = _meeting(idle, settings, uow, generate)
    assert _post(idle, meeting_id, new_story(requested_at="02:00:00")).status_code == 422

    response = _post(idle, meeting_id, new_story())

    assert response.json()["us_id"] == "US-04"


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()["epics"]
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]
    leave_done(settings, meeting_id, status)

    response = idle.post(epic_stories_url(meeting_id, epic_id), json=new_story())

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert idle.get(backlog_url(meeting_id)).json()["epics"] == before


def test_epic_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02."""
    first = _meeting(idle, settings, uow, generate)
    second = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(second)).json()

    response = idle.post(
        epic_stories_url(first, epic_ids(idle, second)["Cadastro"]), json=new_story()
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "epic_not_found"
    assert idle.get(backlog_url(second)).json() == before


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _meeting(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]
    users.use("bia")

    response = idle.post(epic_stories_url(meeting_id, epic_id), json=new_story())

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.post(
        epic_stories_url("00000000-0000-0000-0000-000000000000", 1), json=new_story()
    )

    assert response.status_code == 401
