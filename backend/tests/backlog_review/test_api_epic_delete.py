from collections.abc import Callable

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
    epics_url,
    leave_done,
    with_backlog,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _with_empty_epic(
    client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> str:
    meeting_id = with_backlog(client, settings, uow, generate, ("Cadastro", [story()]))
    assert client.post(epics_url(meeting_id), json={"name": "Vazia"}).status_code == 201
    return meeting_id


def test_empty_epic_is_removed(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 10."""
    meeting_id = _with_empty_epic(idle, settings, uow, generate)

    response = idle.delete(epics_url(meeting_id, epic_ids(idle, meeting_id)["Vazia"]))

    assert response.status_code == 204
    assert list(epic_ids(idle, meeting_id)) == ["Cadastro"]


def test_epic_with_stories_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 10 (Q49): nada muda."""
    meeting_id = _with_empty_epic(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = idle.delete(epics_url(meeting_id, epic_ids(idle, meeting_id)["Cadastro"]))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "epic_not_empty"
    assert idle.get(backlog_url(meeting_id)).json() == before


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _with_empty_epic(idle, settings, uow, generate)
    ids = epic_ids(idle, meeting_id)
    leave_done(settings, meeting_id, status)

    response = idle.delete(epics_url(meeting_id, ids["Vazia"]))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert epic_ids(idle, meeting_id) == ids


def test_epic_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02."""
    first = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    second = _with_empty_epic(idle, settings, uow, generate)

    response = idle.delete(epics_url(first, epic_ids(idle, second)["Vazia"]))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "epic_not_found"
    assert "Vazia" in epic_ids(idle, second)


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _with_empty_epic(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Vazia"]
    users.use("bia")

    response = idle.delete(epics_url(meeting_id, epic_id))

    assert response.status_code == 404
    users.use("ana")
    assert "Vazia" in epic_ids(idle, meeting_id)


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.delete(epics_url("00000000-0000-0000-0000-000000000000", 1))

    assert response.status_code == 401
