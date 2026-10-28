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


def test_new_name_creates_empty_epic_at_end(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 7."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))

    response = idle.post(epics_url(meeting_id), json={"name": "  Relatórios "})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Relatórios"
    epics = idle.get(backlog_url(meeting_id)).json()["epics"]
    assert [(e["id"], e["name"], e["user_stories"]) for e in epics[1:]] == [
        (body["id"], "Relatórios", [])
    ]
    assert epics[0]["name"] == "Cadastro"


def test_existing_name_returns_existing_epic(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 8 (Q57): 200 com a existente, sem mudanças."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    before = idle.get(backlog_url(meeting_id)).json()

    response = idle.post(epics_url(meeting_id), json={"name": " CADASTRO "})

    assert response.status_code == 200
    assert response.json() == {"id": before["epics"][0]["id"], "name": "Cadastro"}
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_same_name_in_other_meeting_does_not_block(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 8: Epic de outra Reunião do mesmo Usuário não impede."""
    with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    meeting_id = with_backlog(idle, settings, uow, generate, ("Vendas", [story()]))

    response = idle.post(epics_url(meeting_id), json={"name": "Cadastro"})

    assert response.status_code == 201
    assert list(epic_ids(idle, meeting_id)) == ["Vendas", "Cadastro"]


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, name: str
) -> None:
    """`backlog-review` 9."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))

    response = idle.post(epics_url(meeting_id), json={"name": name})

    assert response.status_code == 422
    assert list(epic_ids(idle, meeting_id)) == ["Cadastro"]


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    leave_done(settings, meeting_id, status)

    response = idle.post(epics_url(meeting_id), json={"name": "Relatórios"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert list(epic_ids(idle, meeting_id)) == ["Cadastro"]


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    users.use("bia")

    response = idle.post(epics_url(meeting_id), json={"name": "Relatórios"})

    assert response.status_code == 404
    users.use("ana")
    assert list(epic_ids(idle, meeting_id)) == ["Cadastro"]


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.post(epics_url("00000000-0000-0000-0000-000000000000"), json={})

    assert response.status_code == 401
