import sqlite3
from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.events import Event, PartsReady
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers import service as llm_providers
from snook.modules.transcript_split import messages, service
from tests.auth.helpers import rows
from tests.transcript_split.conftest import Prepare
from tests.transcript_split.helpers import confirmed, lines, use_budget

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
STATE = "SELECT status, failed_stage, error_message, split_reason, run_id FROM meetings"
PARTS = 'SELECT "index", start_seconds, end_seconds, estimated_tokens FROM transcript_parts'


def _state(settings: Settings) -> tuple[Any, ...]:
    [row] = rows(settings.database_path, STATE)
    return tuple(row)


def _untouched(settings: Settings) -> list[Any]:
    """Participantes, vínculos e Transcrição (`transcript-split` 24)."""
    return [
        rows(settings.database_path, f"SELECT * FROM {table} ORDER BY 1, 2")  # noqa: S608
        for table in ("participants", "speaker_links", "transcript_segments")
    ]


def test_whole_transcript_fits_saves_single_part(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 1: Parte única, `generating`, `run_id` novo, "Partes prontas" uma vez."""
    meeting_id = confirmed(idle, settings)
    whole = "\n".join(lines(uow, meeting_id))
    use_budget(settings, uow, meeting_id, len(whole))
    old_run = _state(settings)[4]

    assert prepare(meeting_id) == "generating"

    status, stage, message, reason, run_id = _state(settings)
    assert (status, stage, message, reason) == ("generating", None, None, None)
    assert run_id != old_run
    assert rows(settings.database_path, PARTS) == [(1, 0.0, 3730.0, len(whole))]
    assert ready == [PartsReady(meeting_id=meeting_id, run_id=run_id)]


def test_too_long_goes_to_needs_split_without_parts(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 2: `needs_split` com `too_long`; sem Parte, sem aviso."""
    meeting_id = confirmed(idle, settings)
    longest = max(len(line) for line in lines(uow, meeting_id))
    use_budget(settings, uow, meeting_id, longest)
    old_run = _state(settings)[4]

    assert prepare(meeting_id) == "needs_split"

    assert _state(settings) == ("needs_split", None, None, "too_long", old_run)
    assert rows(settings.database_path, PARTS) == []
    assert ready == []


@pytest.mark.parametrize("fits", [True, False])
def test_never_calls_generate(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    prepare: Prepare,
    monkeypatch: pytest.MonkeyPatch,
    fits: bool,
) -> None:
    """`transcript-split` 3."""
    meeting_id = confirmed(idle, settings)
    longest = max(len(line) for line in lines(uow, meeting_id))
    use_budget(settings, uow, meeting_id, 10_000 if fits else longest)
    calls: list[object] = []
    monkeypatch.setattr(llm_providers, "generate", lambda *a, **k: calls.append(a))

    prepare(meeting_id)

    assert calls == []


def test_no_active_provider_fails_pointing_to_settings(
    idle: TestClient, settings: Settings, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 5."""
    meeting_id = confirmed(idle, settings)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("DELETE FROM llm_configs")

    assert prepare(meeting_id) == "failed"

    assert _state(settings)[:4] == ("failed", "generation", messages.NO_ACTIVE_PROVIDER, None)
    assert "Configurações" in messages.NO_ACTIVE_PROVIDER
    assert rows(settings.database_path, PARTS) == []
    assert ready == []


def test_single_segment_over_budget_fails(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 6: sem corte possível no fim de segmento."""
    meeting_id = confirmed(idle, settings)
    longest = max(len(line) for line in lines(uow, meeting_id))
    assert use_budget(settings, uow, meeting_id, longest - 2) < longest

    assert prepare(meeting_id) == "failed"

    assert _state(settings)[:3] == ("failed", "generation", messages.SEGMENT_TOO_LONG)
    assert "janela de contexto maior" in messages.SEGMENT_TOO_LONG
    assert rows(settings.database_path, PARTS) == []
    assert ready == []


@pytest.mark.parametrize("budget", ["fits", "split", "segment", "provider"])
def test_participants_and_transcript_never_change(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, budget: str
) -> None:
    """`transcript-split` 24."""
    meeting_id = confirmed(idle, settings)
    longest = max(len(line) for line in lines(uow, meeting_id))
    if budget == "provider":
        with sqlite3.connect(settings.database_path) as conn:
            conn.execute("DELETE FROM llm_configs")
    else:
        target = {"fits": 10_000, "split": longest, "segment": longest - 2}[budget]
        use_budget(settings, uow, meeting_id, target)
    before = _untouched(settings)

    prepare(meeting_id)

    assert _untouched(settings) == before


def test_estimate_uses_owner_provider_model(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 4: estimativa com o modelo do provedor ativo do dono."""
    meeting_id = confirmed(idle, settings)
    seen: list[tuple[str, str]] = []

    def estimate(provider: str, model: str, text: str) -> int:
        seen.append((provider, model))
        return len(text)

    with uow() as unit:
        service.prepare_generation(unit, meeting_id, "normal", now=_now(idle), estimate=estimate)

    assert set(seen) == {("ollama", "llama3")}


def _now(client: TestClient) -> Any:
    return client.app.state.clock.now()  # type: ignore[attr-defined]
