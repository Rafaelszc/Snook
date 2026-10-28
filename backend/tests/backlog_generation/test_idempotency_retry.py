from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.service import ProviderUnreachable
from snook.modules.transcript_split import service as transcript_split
from tests.auth.helpers import rows
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    generating,
    parts_ready,
    stored_stories,
    story,
)
from tests.diarized_transcription.helpers import state
from tests.meetings.helpers import set_fields
from tests.transcript_split.helpers import FakeEstimate

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
MEETING = "SELECT * FROM meetings"


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "transcribed"},
        {"status": "needs_split", "split_reason": "too_long"},
        {"status": "done", "backlog_saved_at": "2026-10-28T12:00:00Z"},
        {"status": "failed", "failed_stage": "generation", "error_message": "falhou"},
    ],
    ids=["transcribed", "needs_split", "done", "failed"],
)
def test_notice_outside_generating_is_ignored(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    fields: dict[str, str],
) -> None:
    """`backlog-generation` 33: fora de `generating`, nenhuma chamada, nada gravado."""
    meeting_id = generating(idle, settings, uow)
    set_fields(settings.database_path, meeting_id, **fields)
    before = rows(settings.database_path, MEETING)

    parts_ready(idle, meeting_id)

    assert generate.calls == []
    assert rows(settings.database_path, MEETING) == before
    assert stored_stories(settings, meeting_id) == []


def test_second_notice_after_done_is_ignored(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 33: segundo aviso da mesma geração, já concluída."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]
    parts_ready(idle, meeting_id)
    before = rows(settings.database_path, MEETING)

    parts_ready(idle, meeting_id)

    assert len(generate.calls) == 1
    assert rows(settings.database_path, MEETING) == before


def test_second_notice_during_generation_is_ignored(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 33: aviso repetido chega com a geração em curso."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]
    generate.on_call = lambda call: parts_ready(idle, meeting_id) if call == 1 else None

    parts_ready(idle, meeting_id)

    assert len(generate.calls) == 1
    assert state(settings.database_path, meeting_id) == ("done", None, None)
    assert stored_stories(settings, meeting_id) == [(1, "Cadastro", "Cadastrar cliente")]


def test_stale_run_id_is_ignored(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """ADR-0007: aviso com `run_id` velho não gera nada."""
    meeting_id = generating(idle, settings, uow, run_id="run-2")
    before = rows(settings.database_path, MEETING)

    parts_ready(idle, meeting_id, run_id="run-1")

    assert generate.calls == []
    assert rows(settings.database_path, MEETING) == before


def _transcript(settings: Settings) -> list[tuple[object, ...]]:
    return rows(settings.database_path, "SELECT * FROM transcript_segments ORDER BY position")


def test_retry_after_failure_reaches_done(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 29; transversal 16: "Tentar novamente" leva a `done` com a mesma
    Transcrição e os mesmos Participantes."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [ProviderUnreachable("timeout")]
    parts_ready(idle, meeting_id)
    assert state(settings.database_path, meeting_id)[:2] == ("failed", "generation")
    transcript = _transcript(settings)
    people = rows(settings.database_path, "SELECT * FROM participants ORDER BY name")
    app: FastAPI = idle.app  # type: ignore[assignment]
    app.state.prepare_generation = lambda event: transcript_split.on_generation_requested(
        event, uow, now=app.state.clock.now, estimate=FakeEstimate()
    )

    generate.replies = [backlog(("Cadastro", [story()]))]
    assert idle.post(f"/api/meetings/{meeting_id}/retry").status_code == 202

    assert state(settings.database_path, meeting_id) == ("done", None, None)
    assert len(generate.calls) == 2
    assert stored_stories(settings, meeting_id) == [(1, "Cadastro", "Cadastrar cliente")]
    assert _transcript(settings) == transcript
    assert rows(settings.database_path, "SELECT * FROM participants ORDER BY name") == people
