import json
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import FakeGenerate, generating, story
from tests.backlog_review.helpers import (
    NOT_DONE,
    empty_backlog,
    export_url,
    fixture_backlog,
    leave_done,
    with_backlog,
)

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]

SNAPSHOT = Path(__file__).parent / "snapshots" / "backlog.json"


def test_json_matches_snapshot(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 34, 35: título, data, `US-id`, solicitante (nome), quando; sem Parte
    nem `id` interno."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)

    response = idle.get(export_url(meeting_id, "json"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"
    assert response.json() == json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    assert '"id"' not in response.text
    assert "part" not in response.text.lower()


def test_attachment_with_sanitized_name_and_nosniff(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-12."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)

    response = idle.get(export_url(meeting_id, "json"))

    assert response.headers["content-disposition"] == (
        'attachment; filename="planejamento-de-vendas-backlog.json"; '
        "filename*=UTF-8''planejamento-de-vendas-backlog.json"
    )
    assert response.headers["x-content-type-options"] == "nosniff"


def test_script_text_is_exported_as_data(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-12: `<script>` sai como dado no anexo."""
    meeting_id = with_backlog(
        idle, settings, uow, generate, ("<script>alert(1)</script>", [story("<b>x</b>")])
    )

    response = idle.get(export_url(meeting_id, "json"))

    body = response.json()
    assert body["epics"][0]["name"] == "<script>alert(1)</script>"
    assert body["epics"][0]["user_stories"][0]["name"] == "<b>x</b>"
    assert response.headers["content-disposition"].startswith("attachment;")


def test_empty_backlog_returns_only_header(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 36, 47."""
    meeting_id = empty_backlog(idle, settings, uow, generate)

    response = idle.get(export_url(meeting_id, "json"))

    assert response.json() == {"title": "Planejamento de Vendas", "date": "2026-10-23", "epics": []}


@pytest.mark.parametrize("status", NOT_DONE)
def test_works_in_every_status_with_backlog(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 31."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    leave_done(settings, meeting_id, status)

    response = idle.get(export_url(meeting_id, "json"))

    assert response.status_code == 200
    assert response.json() == json.loads(SNAPSHOT.read_text(encoding="utf-8"))


def test_without_backlog_is_409(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`backlog-review` 31."""
    meeting_id = generating(idle, settings, uow)

    response = idle.get(export_url(meeting_id, "json"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_backlog"


@pytest.mark.parametrize("query", ["?format=csv", "?format=", ""])
def test_unknown_format_is_422(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, query: str
) -> None:
    """`05-api.md`: formato desconhecido, 422."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)

    response = idle.get(f"/api/meetings/{meeting_id}/export{query}")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    users.use("bia")

    response = idle.get(export_url(meeting_id, "json"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.get(export_url("00000000-0000-0000-0000-000000000000", "json"))

    assert response.status_code == 401
