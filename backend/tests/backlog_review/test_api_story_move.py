from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.backlog_generation.helpers import FakeGenerate, story
from tests.backlog_review.helpers import (
    backlog_url,
    epic_ids,
    participant_ids,
    stories,
    stories_url,
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


def _patch(client: TestClient, meeting_id: str, body: dict[str, Any]) -> Any:
    story_id = stories(client, meeting_id)["US-01"]["id"]
    return client.patch(stories_url(meeting_id, story_id), json=body)


def test_requester_changes_to_other_participant(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 14."""
    meeting_id = _meeting(idle, settings, uow, generate)
    bia = participant_ids(idle, meeting_id)["Bia"]

    response = _patch(idle, meeting_id, {"requested_by": bia})

    assert response.status_code == 200
    assert response.json()["requested_by"] == {"id": bia, "name": "Bia"}
    assert stories(idle, meeting_id)["US-01"]["requested_by"] == {"id": bia, "name": "Bia"}


def test_requester_can_be_cleared(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 14."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _patch(idle, meeting_id, {"requested_by": None})

    assert response.status_code == 200
    assert stories(idle, meeting_id)["US-01"]["requested_by"] is None


def test_requester_of_other_meeting_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 14: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    other = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _patch(idle, meeting_id, {"requested_by": participant_ids(idle, other)["Bia"]})

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["requested_by"]
    assert idle.get(backlog_url(meeting_id)).json() == before


@pytest.mark.parametrize("value", ["00:00:00", "01:00:00", "01:06:40"])
def test_requested_at_within_duration_is_saved(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, value: str
) -> None:
    """`backlog-review` 15: entre 0 e a duração (4000 s = 01:06:40)."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _patch(idle, meeting_id, {"requested_at": value})

    assert response.status_code == 200
    assert stories(idle, meeting_id)["US-01"]["requested_at"] == value


@pytest.mark.parametrize("value", ["01:06:41", "1:00:00", "00:60:00", "00:00:5", "-00:00:01", 60])
def test_requested_at_invalid_or_after_duration_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, value: Any
) -> None:
    """`backlog-review` 15: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _patch(idle, meeting_id, {"requested_at": value})

    assert response.status_code == 422
    assert list(response.json()["error"]["fields"]) == ["requested_at"]
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_requested_at_can_be_cleared(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 15, 18: instante opcional (Q56)."""
    meeting_id = _meeting(idle, settings, uow, generate)

    response = _patch(idle, meeting_id, {"requested_at": None})

    assert response.status_code == 200
    assert stories(idle, meeting_id)["US-01"]["requested_at"] is None


def test_move_goes_to_end_of_target_and_keeps_us_id(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 16: origem pode ficar vazia."""
    meeting_id = _meeting(idle, settings, uow, generate)
    ids = epic_ids(idle, meeting_id)

    response = _patch(idle, meeting_id, {"epic_id": ids["Relatórios"]})

    assert response.status_code == 200
    assert response.json()["us_id"] == "US-01"
    epics = idle.get(backlog_url(meeting_id)).json()["epics"]
    assert [(e["name"], [s["us_id"] for s in e["user_stories"]]) for e in epics] == [
        ("Cadastro", []),
        ("Relatórios", ["US-02", "US-03", "US-01"]),
    ]


def test_move_to_same_epic_keeps_position(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 16: só Epic diferente move."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()
    story_id = stories(idle, meeting_id)["US-02"]["id"]

    response = idle.patch(
        stories_url(meeting_id, story_id),
        json={"epic_id": epic_ids(idle, meeting_id)["Relatórios"]},
    )

    assert response.status_code == 200
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_move_to_epic_of_other_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 37; SEC-02: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    other = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()

    response = _patch(idle, meeting_id, {"epic_id": epic_ids(idle, other)["Relatórios"]})

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "epic_not_found"
    assert idle.get(backlog_url(meeting_id)).json() == before


def test_invalid_field_with_move_changes_nothing(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 15, 16: erro em um campo não grava os outros."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()
    target = epic_ids(idle, meeting_id)["Relatórios"]

    response = _patch(
        idle, meeting_id, {"epic_id": target, "name": "Outro", "requested_at": "02:00:00"}
    )

    assert response.status_code == 422
    assert idle.get(backlog_url(meeting_id)).json() == before
