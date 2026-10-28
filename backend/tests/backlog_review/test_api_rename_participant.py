from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import FakeGenerate, story
from tests.backlog_review.helpers import (
    backlog_url,
    leave_done,
    participant_ids,
    stories,
    with_backlog,
)
from tests.diarized_transcription.helpers import create

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _meeting(client: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate) -> str:
    return with_backlog(
        client,
        settings,
        uow,
        generate,
        ("Cadastro", [story("Cadastrar cliente"), story("Editar cliente", requested_by="Bia")]),
        ("Relatórios", [story("Exportar vendas", requested_by="Bia")]),
    )


def _url(meeting_id: str, participant_id: int) -> str:
    return f"/api/meetings/{meeting_id}/participants/{participant_id}"


def _requesters(client: TestClient, meeting_id: str) -> dict[str, Any]:
    return {us_id: s["requested_by"] for us_id, s in stories(client, meeting_id).items()}


def _without_requesters(backlog: dict[str, Any]) -> list[Any]:
    """Epics e US sem o solicitante: o que a renomeação não pode mudar."""
    return [
        {
            **epic,
            "user_stories": [
                {k: v for k, v in s.items() if k != "requested_by"} for s in epic["user_stories"]
            ],
        }
        for epic in backlog["epics"]
    ]


def test_new_name_shows_in_requesters(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 23."""
    meeting_id = _meeting(idle, settings, uow, generate)
    bia = participant_ids(idle, meeting_id)["Bia"]

    response = idle.patch(_url(meeting_id, bia), json={"name": " Beatriz "})

    assert response.status_code == 200
    assert response.json() == {
        "participant": {"id": bia, "name": "Beatriz", "speaker_labels": ["SPEAKER_01"]},
        "absorbed_id": None,
    }
    beatriz = {"id": bia, "name": "Beatriz"}
    assert _requesters(idle, meeting_id)["US-02"] == beatriz
    assert _requesters(idle, meeting_id)["US-03"] == beatriz


def test_name_of_other_participant_merges_and_moves_requesters(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 24: sobrevive quem já tinha o nome; US do absorvido passam a ele."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, meeting_id)

    response = idle.patch(_url(meeting_id, ids["Bia"]), json={"name": "ana"})

    assert response.status_code == 200
    assert response.json() == {
        "participant": {
            "id": ids["Ana"],
            "name": "Ana",
            "speaker_labels": ["SPEAKER_00", "SPEAKER_01"],
        },
        "absorbed_id": ids["Bia"],
    }
    ana = {"id": ids["Ana"], "name": "Ana"}
    assert _requesters(idle, meeting_id) == {"US-01": ana, "US-02": ana, "US-03": ana}
    assert participant_ids(idle, meeting_id) == {"Ana": ids["Ana"]}


def test_rename_does_not_call_llm_nor_change_texts(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 25; transversal 17."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, meeting_id)
    calls = len(generate.calls)
    before = idle.get(backlog_url(meeting_id)).json()

    assert idle.patch(_url(meeting_id, ids["Ana"]), json={"name": "Aninha"}).status_code == 200
    assert idle.patch(_url(meeting_id, ids["Bia"]), json={"name": "Aninha"}).status_code == 200

    assert len(generate.calls) == calls
    after = idle.get(backlog_url(meeting_id)).json()
    assert _without_requesters(after) == _without_requesters(before)
    assert after["read_only"] is False


@pytest.mark.parametrize("status", ["transcribed", "needs_split", "failed"])
def test_allowed_outside_done_except_generating(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30 (`participants` 21)."""
    meeting_id = _meeting(idle, settings, uow, generate)
    bia = participant_ids(idle, meeting_id)["Bia"]
    leave_done(settings, meeting_id, status)

    response = idle.patch(_url(meeting_id, bia), json={"name": "Beatriz"})

    assert response.status_code == 200
    assert _requesters(idle, meeting_id)["US-02"] == {"id": bia, "name": "Beatriz"}


def test_generating_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, meeting_id)
    before = _requesters(idle, meeting_id)
    leave_done(settings, meeting_id, "generating")

    response = idle.patch(_url(meeting_id, ids["Bia"]), json={"name": "Ana"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status"
    assert participant_ids(idle, meeting_id) == ids
    assert _requesters(idle, meeting_id) == before


def test_without_confirmed_participants_is_409(idle: TestClient) -> None:
    """`backlog-review` 30 (`participants` 21)."""
    meeting_id = create(idle)

    response = idle.patch(_url(meeting_id, 1), json={"name": "Ana"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "not_confirmed"


@pytest.mark.parametrize("name", ["", "   ", "x" * 101])
def test_invalid_name_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, name: str
) -> None:
    """`participants` 8; SEC-09: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, meeting_id)

    response = idle.patch(_url(meeting_id, ids["Bia"]), json={"name": name})

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["name"]
    assert participant_ids(idle, meeting_id) == ids


def test_participant_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02: nada muda."""
    first = _meeting(idle, settings, uow, generate)
    second = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, second)

    response = idle.patch(_url(first, ids["Bia"]), json={"name": "Ana"})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "participant_not_found"
    assert participant_ids(idle, second) == ids


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = participant_ids(idle, meeting_id)
    users.use("bia")

    response = idle.patch(_url(meeting_id, ids["Bia"]), json={"name": "Ana"})

    assert response.status_code == 404
    users.use("ana")
    assert participant_ids(idle, meeting_id) == ids


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.patch(_url("00000000-0000-0000-0000-000000000000", 1), json={"name": "Ana"})

    assert response.status_code == 401
