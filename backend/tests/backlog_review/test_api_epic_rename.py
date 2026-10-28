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


def _two_epics(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(
        client,
        settings,
        uow,
        generate,
        ("Cadastro", [story("Cadastrar cliente")]),
        ("Relatórios", [story("Exportar vendas"), story("Imprimir vendas")]),
    )


def test_rename_saves_trimmed_name(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 5."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]

    response = idle.patch(epics_url(meeting_id, epic_id), json={"name": "  Clientes  "})

    assert response.status_code == 200
    assert response.json() == {"id": epic_id, "name": "Clientes", "merged_into": None}
    assert list(epic_ids(idle, meeting_id)) == ["Clientes", "Relatórios"]


def test_rename_changing_only_case_keeps_epic(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 5: mesmo nome normalizado da própria Epic não é junção."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]

    response = idle.patch(epics_url(meeting_id, epic_id), json={"name": "CADASTRO"})

    assert response.status_code == 200
    assert response.json() == {"id": epic_id, "name": "CADASTRO", "merged_into": None}


def test_rename_to_existing_name_merges_into_it(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 6: sobrevive a que tinha o nome; US da renomeada vão depois."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    ids = epic_ids(idle, meeting_id)

    response = idle.patch(epics_url(meeting_id, ids["Cadastro"]), json={"name": " relatórios "})

    assert response.status_code == 200
    assert response.json() == {
        "id": ids["Relatórios"],
        "name": "Relatórios",
        "merged_into": ids["Relatórios"],
    }
    epics = idle.get(backlog_url(meeting_id)).json()["epics"]
    assert [(e["id"], e["name"]) for e in epics] == [(ids["Relatórios"], "Relatórios")]
    stories = [(s["us_id"], s["name"]) for s in epics[0]["user_stories"]]
    assert stories == [
        ("US-02", "Exportar vendas"),
        ("US-03", "Imprimir vendas"),
        ("US-01", "Cadastrar cliente"),
    ]


@pytest.mark.parametrize("name", ["", "   "])
def test_empty_name_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, name: str
) -> None:
    """`backlog-review` 9."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]

    response = idle.patch(epics_url(meeting_id, epic_id), json={"name": name})

    assert response.status_code == 422
    assert list(epic_ids(idle, meeting_id)) == ["Cadastro", "Relatórios"]


def test_name_above_max_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-09: nome de Epic até 200."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]

    response = idle.patch(epics_url(meeting_id, epic_id), json={"name": "x" * 201})

    assert response.status_code == 422


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    ids = epic_ids(idle, meeting_id)
    leave_done(settings, meeting_id, status)

    response = idle.patch(epics_url(meeting_id, ids["Cadastro"]), json={"name": "Relatórios"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert epic_ids(idle, meeting_id) == ids


def test_epic_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02."""
    first = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    second = with_backlog(idle, settings, uow, generate, ("Vendas", [story()]))
    other_epic = epic_ids(idle, second)["Vendas"]

    response = idle.patch(epics_url(first, other_epic), json={"name": "Outra"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "epic_not_found"
    assert list(epic_ids(idle, second)) == ["Vendas"]


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _two_epics(idle, settings, uow, generate)
    epic_id = epic_ids(idle, meeting_id)["Cadastro"]
    users.use("bia")

    response = idle.patch(epics_url(meeting_id, epic_id), json={"name": "Outra"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.patch(epics_url("00000000-0000-0000-0000-000000000000", 1), json={})

    assert response.status_code == 401
