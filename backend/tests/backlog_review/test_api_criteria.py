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
    criteria_url,
    leave_done,
    stories,
    with_backlog,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]

CRITERION = {"given": "carrinho cheio", "when": "fecho o pedido", "then": "recebo o número"}


def _meeting(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(
        client,
        settings,
        uow,
        generate,
        ("Cadastro", [story("Cadastrar cliente", criteria=2), story("Editar cliente")]),
    )


def _criteria(client: TestClient, meeting_id: str, us_id: str = "US-01") -> list[dict[str, Any]]:
    criteria: list[dict[str, Any]] = stories(client, meeting_id)[us_id]["acceptance_criteria"]
    return criteria


def _story_id(client: TestClient, meeting_id: str, us_id: str = "US-01") -> int:
    story_id: int = stories(client, meeting_id)[us_id]["id"]
    return story_id


def test_post_adds_criterion_at_end(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 20."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = _criteria(idle, meeting_id)
    url = criteria_url(meeting_id, story_id=_story_id(idle, meeting_id))

    response = idle.post(url, json={**CRITERION, "given": "  carrinho cheio "})

    assert response.status_code == 201
    body = response.json()
    assert {key: body[key] for key in CRITERION} == CRITERION
    assert _criteria(idle, meeting_id) == [*before, body]


@pytest.mark.parametrize(
    "body",
    [
        {**CRITERION, "given": ""},
        {**CRITERION, "when": "   "},
        {**CRITERION, "then": None},
        {"given": "a", "when": "b"},
        {**CRITERION, "then": "x" * 1001},
        {**CRITERION, "extra": "x"},
    ],
)
def test_post_invalid_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, body: dict[str, Any]
) -> None:
    """`backlog-review` 20; SEC-09: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = idle.post(criteria_url(meeting_id, story_id=_story_id(idle, meeting_id)), json=body)

    assert response.status_code == 422
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_patch_saves_sent_fields(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 21."""
    meeting_id = _meeting(idle, settings, uow, generate)
    first, second = _criteria(idle, meeting_id)

    response = idle.patch(
        criteria_url(meeting_id, criterion_id=first["id"]), json={"then": " cliente salvo "}
    )

    assert response.status_code == 200
    assert response.json() == {**first, "then": "cliente salvo"}
    assert _criteria(idle, meeting_id) == [{**first, "then": "cliente salvo"}, second]


@pytest.mark.parametrize("field", ["given", "when", "then"])
@pytest.mark.parametrize("value", ["", "  ", None])
def test_patch_empty_field_is_422(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    field: str,
    value: str | None,
) -> None:
    """`backlog-review` 21: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = _criteria(idle, meeting_id)

    response = idle.patch(
        criteria_url(meeting_id, criterion_id=before[0]["id"]), json={field: value}
    )

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == [field]
    assert _criteria(idle, meeting_id) == before


def test_patch_above_max_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-09: `given`, `when`, `then` até 1000."""
    meeting_id = _meeting(idle, settings, uow, generate)
    criterion_id = _criteria(idle, meeting_id)[0]["id"]

    response = idle.patch(
        criteria_url(meeting_id, criterion_id=criterion_id), json={"when": "x" * 1001}
    )

    assert response.status_code == 422


def test_delete_removes_criterion(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 22: com outro critério na US, sai."""
    meeting_id = _meeting(idle, settings, uow, generate)
    first, second = _criteria(idle, meeting_id)

    response = idle.delete(criteria_url(meeting_id, criterion_id=first["id"]))

    assert response.status_code == 204
    assert _criteria(idle, meeting_id) == [second]


def test_delete_last_criterion_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 22: toda US tem pelo menos um critério."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()
    (only,) = _criteria(idle, meeting_id, "US-02")

    response = idle.delete(criteria_url(meeting_id, criterion_id=only["id"]))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "last_criterion"
    assert idle.get(backlog_url(meeting_id)).json() == before


def _requests(client: TestClient, meeting_id: str, story_id: int, criterion_id: int) -> list[Any]:
    """Uma chamada por rota de critério."""
    return [
        lambda: client.post(criteria_url(meeting_id, story_id=story_id), json=CRITERION),
        lambda: client.patch(criteria_url(meeting_id, criterion_id=criterion_id), json=CRITERION),
        lambda: client.delete(criteria_url(meeting_id, criterion_id=criterion_id)),
    ]


ROUTES = ["post", "patch", "delete"]


@pytest.mark.parametrize("status", NOT_DONE)
@pytest.mark.parametrize("route", range(3), ids=ROUTES)
def test_outside_done_is_409(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    status: str,
    route: int,
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()["epics"]
    story_id = _story_id(idle, meeting_id)
    criterion_id = _criteria(idle, meeting_id)[0]["id"]
    leave_done(settings, meeting_id, status)

    response = _requests(idle, meeting_id, story_id, criterion_id)[route]()

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert idle.get(backlog_url(meeting_id)).json()["epics"] == before


@pytest.mark.parametrize(
    ("route", "code"),
    [(0, "story_not_found"), (1, "criterion_not_found"), (2, "criterion_not_found")],
    ids=ROUTES,
)
def test_ids_of_other_meeting_are_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, route: int, code: str
) -> None:
    """`backlog-review` 37; SEC-02: nada muda."""
    first = _meeting(idle, settings, uow, generate)
    second = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(second)).json()
    story_id = _story_id(idle, second)
    criterion_id = _criteria(idle, second)[0]["id"]

    response = _requests(idle, first, story_id, criterion_id)[route]()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == code
    assert idle.get(backlog_url(second)).json() == before


@pytest.mark.parametrize("route", range(3), ids=ROUTES)
def test_other_users_meeting_is_404(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    users: Users,
    route: int,
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()
    story_id = _story_id(idle, meeting_id)
    criterion_id = _criteria(idle, meeting_id)[0]["id"]
    users.use("bia")

    response = _requests(idle, meeting_id, story_id, criterion_id)[route]()

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    users.use("ana")
    assert idle.get(backlog_url(meeting_id)).json() == before


@pytest.mark.parametrize("route", range(3), ids=ROUTES)
def test_without_session_is_401(client: TestClient, route: int) -> None:
    """`backlog-review` 38; SEC-01."""
    response = _requests(client, "00000000-0000-0000-0000-000000000000", 1, 1)[route]()

    assert response.status_code == 401
