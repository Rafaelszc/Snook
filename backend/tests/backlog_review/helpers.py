from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.backlog_generation.helpers import FakeGenerate, backlog, generating, parts_ready
from tests.diarized_transcription.helpers import state
from tests.meetings.helpers import set_fields


def backlog_url(meeting_id: str) -> str:
    return f"/api/meetings/{meeting_id}/backlog"


def with_backlog(
    client: TestClient,
    settings: Settings,
    uow: Callable[[], UnitOfWork],
    generate: FakeGenerate,
    *epics: tuple[str, list[dict[str, Any]]],
) -> str:
    """Reunião em `done` com o backlog `epics` gravado pela geração (Parte única)."""
    meeting_id = generating(client, settings, uow)
    generate.replies = [backlog(*epics)]
    parts_ready(client, meeting_id)
    assert state(settings.database_path, meeting_id)[0] == "done"
    return meeting_id


def epics_url(meeting_id: str, epic_id: int | None = None) -> str:
    base = f"/api/meetings/{meeting_id}/epics"
    return base if epic_id is None else f"{base}/{epic_id}"


def epic_ids(client: TestClient, meeting_id: str) -> dict[str, int]:
    """Nome da Epic → `id`, pelo `GET /backlog`."""
    epics = client.get(backlog_url(meeting_id)).json()["epics"]
    return {epic["name"]: epic["id"] for epic in epics}


def leave_done(settings: Settings, meeting_id: str, status: str) -> None:
    """Tira a Reunião de `done` mantendo o backlog gravado (`backlog-review` 30)."""
    extra: dict[str, Any] = {}
    if status == "failed":
        extra = {"failed_stage": "generation", "error_message": "Falha."}
    if status == "needs_split":
        extra = {"split_reason": "too_long"}
    set_fields(settings.database_path, meeting_id, status=status, **extra)


NOT_DONE = ["transcribed", "generating", "needs_split", "failed"]


def stories_url(meeting_id: str, story_id: int) -> str:
    return f"/api/meetings/{meeting_id}/user-stories/{story_id}"


def epic_stories_url(meeting_id: str, epic_id: int) -> str:
    return f"{epics_url(meeting_id, epic_id)}/user-stories"


def criteria_url(meeting_id: str, *, story_id: int | None = None, criterion_id: int = 0) -> str:
    """Com `story_id`: rota de criar; sem: `PATCH`/`DELETE` do critério."""
    if story_id is not None:
        return f"{stories_url(meeting_id, story_id)}/criteria"
    return f"/api/meetings/{meeting_id}/criteria/{criterion_id}"


def stories(client: TestClient, meeting_id: str) -> dict[str, dict[str, Any]]:
    """`US-id` → US do `GET /backlog`, com o nome da Epic em `epic`."""
    epics = client.get(backlog_url(meeting_id)).json()["epics"]
    return {s["us_id"]: {**s, "epic": epic["name"]} for epic in epics for s in epic["user_stories"]}


def participant_ids(client: TestClient, meeting_id: str) -> dict[str, int]:
    """Nome do Participante → `id`."""
    found = client.get(f"/api/meetings/{meeting_id}/participants").json()
    return {p["name"]: p["id"] for p in found}


def new_story(**overrides: Any) -> dict[str, Any]:
    """Corpo de `POST .../user-stories`, sem solicitante nem instante."""
    return {
        "name": "Emitir nota",
        "as_a": "vendedor",
        "i_want": "emitir nota fiscal",
        "so_that": "o cliente receba o comprovante",
        "priority": "Medium",
        "story_points": 3,
        "acceptance_criteria": [{"given": "pedido pago", "when": "emito", "then": "nota sai"}],
        **overrides,
    }
