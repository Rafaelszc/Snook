from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import Users
from tests.backlog_generation.helpers import FakeGenerate, generating
from tests.backlog_review.helpers import (
    NOT_DONE,
    empty_backlog,
    export_url,
    fixture_backlog,
    leave_done,
)
from tests.meetings.helpers import set_fields

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]

SNAPSHOT = Path(__file__).parent / "snapshots" / "backlog.md"


def test_markdown_matches_snapshot(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 32, 33, 35: documento de Product Backlog (Q75)."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)

    response = idle.get(export_url(meeting_id, "md"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/markdown; charset=utf-8"
    assert response.text == SNAPSHOT.read_text(encoding="utf-8")
    assert "part" not in response.text.lower()


def test_attachment_with_sanitized_name_and_nosniff(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """SEC-12: anexo, nome sanitizado, `nosniff`."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    set_fields(settings.database_path, meeting_id, title='Reunião: "Vendas" / Q4 <script>')

    response = idle.get(export_url(meeting_id, "md"))

    assert response.headers["content-disposition"] == (
        'attachment; filename="backlog_reuniao-vendas-q4-script_2026-10-23.md"; '
        "filename*=UTF-8''backlog_reuniao-vendas-q4-script_2026-10-23.md"
    )
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("!!!", "backlog_reuniao_2026-10-23.md"),
        ("日本語", "backlog_reuniao_2026-10-23.md"),
        ("a" * 80, f"backlog_{'a' * 60}_2026-10-23.md"),
        ("Ação " + "b" * 58 + " c", f"backlog_acao-{'b' * 55}_2026-10-23.md"),
    ],
)
def test_slug_is_ascii_up_to_60_and_never_empty(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    title: str,
    expected: str,
) -> None:
    """SEC-12; `05-api.md`: `backlog_<slug>_<data>.md`, slug `[a-z0-9-]` até 60, vazio `reuniao`."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    set_fields(settings.database_path, meeting_id, title=title)

    response = idle.get(export_url(meeting_id, "md"))

    assert f'filename="{expected}"' in response.headers["content-disposition"]


def test_empty_backlog_returns_only_header(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-review` 36, 47."""
    meeting_id = empty_backlog(idle, settings, uow, generate)

    response = idle.get(export_url(meeting_id, "md"))

    assert response.status_code == 200
    assert response.text == (
        "# Product Backlog: Planejamento de Vendas\n\n"
        "- **Reunião:** Planejamento de Vendas\n"
        "- **Data:** 2026-10-23\n"
        "- **Projeto:** Planejamento de Vendas\n"
        "- **Épicos:** 0\n"
        "- **Histórias de usuário:** 0\n"
        "- **Story Points:** 0\n"
    )


@pytest.mark.parametrize("status", NOT_DONE)
def test_works_in_every_status_with_backlog(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, status: str
) -> None:
    """`backlog-review` 31."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    leave_done(settings, meeting_id, status)

    response = idle.get(export_url(meeting_id, "md"))

    assert response.status_code == 200
    assert response.text == SNAPSHOT.read_text(encoding="utf-8")


def test_without_backlog_is_409(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`backlog-review` 31."""
    meeting_id = generating(idle, settings, uow)

    response = idle.get(export_url(meeting_id, "md"))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "no_backlog"


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate, users: Users
) -> None:
    """`backlog-review` 37; SEC-02."""
    meeting_id = fixture_backlog(idle, settings, uow, generate)
    users.use("bia")

    response = idle.get(export_url(meeting_id, "md"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`backlog-review` 38; SEC-01."""
    response = client.get(export_url("00000000-0000-0000-0000-000000000000", "md"))

    assert response.status_code == 401
