from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users, rows
from tests.backlog_generation.helpers import FakeGenerate, generating, story
from tests.backlog_review.helpers import backlog_url, with_backlog
from tests.meetings.helpers import set_fields

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _participant_id(settings: Settings, meeting_id: str, name: str) -> int:
    query = f"SELECT id FROM participants WHERE meeting_id = '{meeting_id}' AND name = '{name}'"  # noqa: S608
    return int(rows(settings.database_path, query)[0][0])


def test_done_returns_epics_and_stories_in_order(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 1, 2: Epics e US em ordem, todos os campos, sem Parte."""
    meeting_id = with_backlog(
        idle,
        settings,
        uow,
        generate,
        (
            "Cadastro",
            [story("Cadastrar cliente", criteria=2), story("Buscar cliente", requested_by=None)],
        ),
        ("Relatórios", [story("Exportar vendas", requested_by="Bia", requested_at="01:02:03")]),
    )
    ana_id = _participant_id(settings, meeting_id, "Ana")
    bia_id = _participant_id(settings, meeting_id, "Bia")

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 200
    body = response.json()
    assert body["read_only"] is False
    assert body["last_generation_failed"] is False
    assert [epic["name"] for epic in body["epics"]] == ["Cadastro", "Relatórios"]
    first, second = body["epics"][0]["user_stories"]
    assert set(body["epics"][0]) == {"id", "name", "user_stories"}
    assert {k: v for k, v in first.items() if k not in ("id", "acceptance_criteria")} == {
        "us_id": "US-01",
        "name": "Cadastrar cliente",
        "as_a": "atendente",
        "i_want": "cadastrar cliente com CPF",
        "so_that": "eu possa abrir pedidos",
        "priority": "High",
        "story_points": 5,
        "requested_by": {"id": ana_id, "name": "Ana"},
        "requested_at": "00:00:05",
    }
    assert [{k: v for k, v in c.items() if k != "id"} for c in first["acceptance_criteria"]] == [
        {"given": "dado 1", "when": "quando 1", "then": "então 1"},
        {"given": "dado 2", "when": "quando 2", "then": "então 2"},
    ]
    assert (second["us_id"], second["name"], second["requested_by"]) == (
        "US-02",
        "Buscar cliente",
        None,
    )
    third = body["epics"][1]["user_stories"][0]
    assert (third["us_id"], third["requested_by"], third["requested_at"]) == (
        "US-03",
        {"id": bia_id, "name": "Bia"},
        "01:02:03",
    )
    assert "part" not in response.text.lower()


def test_failed_generation_with_backlog_is_read_only_and_flagged(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 3: `failed` na geração devolve o backlog anterior com o indicador."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="Falha.",
    )

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 200
    body = response.json()
    assert (body["read_only"], body["last_generation_failed"]) == (True, True)
    assert body["epics"][0]["user_stories"][0]["name"] == "Cadastrar cliente"


@pytest.mark.parametrize("status", ["transcribed", "generating", "needs_split"])
def test_previous_backlog_is_read_only(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 3: backlog anterior só para leitura fora de `done`."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    split_reason = "too_long" if status == "needs_split" else None
    set_fields(settings.database_path, meeting_id, status=status, split_reason=split_reason)

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 200
    body = response.json()
    assert (body["read_only"], body["last_generation_failed"]) == (True, False)
    assert len(body["epics"]) == 1


@pytest.mark.parametrize("status", ["transcribed", "generating", "failed"])
def test_without_saved_backlog_is_409(
    idle: TestClient, settings: Settings, uow: Uow, status: str
) -> None:
    """`backlog-review` 4."""
    meeting_id = generating(idle, settings, uow)
    failed = {"failed_stage": "generation", "error_message": "Falha."} if status == "failed" else {}
    set_fields(settings.database_path, meeting_id, status=status, **failed)

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_backlog"


def test_done_without_stories_is_empty_list(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 47."""
    meeting_id = with_backlog(idle, settings, uow, generate)

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 200
    assert response.json() == {"read_only": False, "last_generation_failed": False, "epics": []}


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = with_backlog(idle, settings, uow, generate, ("Cadastro", [story()]))
    users.use("bia")

    response = idle.get(backlog_url(meeting_id))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.get(backlog_url("00000000-0000-0000-0000-000000000000"))

    assert response.status_code == 401
