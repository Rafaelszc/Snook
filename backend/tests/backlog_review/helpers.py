from collections.abc import Callable
from typing import Any

from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.backlog_generation.helpers import FakeGenerate, backlog, generating, parts_ready
from tests.diarized_transcription.helpers import state


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
