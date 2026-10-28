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
