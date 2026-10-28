from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import FakeGenerate, count, story
from tests.backlog_review.helpers import (
    NOT_DONE,
    backlog_url,
    epic_ids,
    epic_stories_url,
    leave_done,
    new_story,
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
        ("Cadastro", [story("Cadastrar cliente", criteria=2)]),
        ("Relatórios", [story("Exportar vendas"), story("Imprimir vendas", criteria=3)]),
    )


def test_delete_removes_story_with_criteria(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 19: outros `US-id` não mudam."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = stories(idle, meeting_id)
    assert count(settings, "acceptance_criteria") == 6

    response = idle.delete(stories_url(meeting_id, before["US-02"]["id"]))

    assert response.status_code == 204
    after = stories(idle, meeting_id)
    assert after == {us_id: s for us_id, s in before.items() if us_id != "US-02"}
    assert count(settings, "acceptance_criteria") == 5


def test_deleted_highest_number_is_not_reused(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 19."""
    meeting_id = _meeting(idle, settings, uow, generate)
    assert (
        idle.delete(stories_url(meeting_id, stories(idle, meeting_id)["US-03"]["id"])).status_code
        == 204
    )

    response = idle.post(
        epic_stories_url(meeting_id, epic_ids(idle, meeting_id)["Cadastro"]), json=new_story()
    )

    assert response.json()["us_id"] == "US-04"


@pytest.mark.parametrize("status", NOT_DONE)
def test_outside_done_is_409(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 30: nada muda."""
    meeting_id = _meeting(idle, settings, uow, generate)
    before = idle.get(backlog_url(meeting_id)).json()["epics"]
    story_id = stories(idle, meeting_id)["US-01"]["id"]
    leave_done(settings, meeting_id, status)

    response = idle.delete(stories_url(meeting_id, story_id))

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

    response = idle.delete(stories_url(first, before["US-01"]["id"]))

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

    response = idle.delete(stories_url(meeting_id, before["US-01"]["id"]))

    assert response.status_code == 404
    users.use("ana")
    assert stories(idle, meeting_id) == before


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.delete(stories_url("00000000-0000-0000-0000-000000000000", 1))

    assert response.status_code == 401
