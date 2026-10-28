from collections.abc import Callable
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.events import Event, PartsReady
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.transcript_split import service
from tests.auth.helpers import rows
from tests.meetings.helpers import set_fields
from tests.transcript_split.conftest import Prepare
from tests.transcript_split.helpers import FakeEstimate, confirmed, lines, use_budget

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
STATE = "SELECT status, split_reason, run_id FROM meetings"
PART_ROWS = 'SELECT id, "index", first_segment_id, last_segment_id FROM transcript_parts'
SPLIT = [(0, 0), (1, 2)]


def _state(settings: Settings) -> tuple[Any, ...]:
    [row] = rows(settings.database_path, STATE)
    return tuple(row)


def _divided(idle: TestClient, settings: Settings, uow: Uow, status: str) -> str:
    """Reunião em `status`, já dividida em SPLIT."""
    meeting_id = confirmed(idle, settings)
    snapshot = ActiveProvider(provider="ollama", model="llama3", context_window=100_000)
    with uow() as unit:
        service.save_parts(unit, snapshot, meeting_id, SPLIT, estimate=FakeEstimate())
    if status == "done":
        set_fields(
            settings.database_path, meeting_id, status="done", backlog_saved_at="2026-10-28T12:00Z"
        )
    return meeting_id


def _ranges(uow: Uow, meeting_id: str) -> list[tuple[int, int]]:
    with uow() as unit:
        return [(p.first, p.last) for p in service.list_parts(unit, meeting_id)]


def _sizes(uow: Uow, meeting_id: str) -> tuple[int, int, int]:
    """Maior linha, maior Parte de SPLIT e Transcrição inteira, em tokens fake."""
    found = lines(uow, meeting_id)
    second = len("\n".join(found[1:]))
    return max(len(line) for line in found), second, len("\n".join(found))


@pytest.fixture(params=["transcribed", "done"])
def status(request: pytest.FixtureRequest) -> str:
    """`transcript-split` 23: modo `normal` em `done` segue as regras de 19 a 21."""
    value: str = request.param
    return value


def test_whole_fits_replaces_previous_split(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    prepare: Prepare,
    ready: list[Event],
    status: str,
) -> None:
    """`transcript-split` 19: Parte única mesmo com divisão anterior."""
    meeting_id = _divided(idle, settings, uow, status)
    use_budget(settings, uow, meeting_id, _sizes(uow, meeting_id)[2])

    assert prepare(meeting_id) == "generating"

    assert _ranges(uow, meeting_id) == [(0, 2)]
    assert ready == [PartsReady(meeting_id=meeting_id, run_id=_state(settings)[2])]


def test_previous_parts_that_fit_are_reused(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    prepare: Prepare,
    ready: list[Event],
    status: str,
) -> None:
    """`transcript-split` 20 e 38: reaproveita sem regravar."""
    meeting_id = _divided(idle, settings, uow, status)
    _, second, whole = _sizes(uow, meeting_id)
    assert use_budget(settings, uow, meeting_id, second) < whole
    before = rows(settings.database_path, PART_ROWS)

    assert prepare(meeting_id) == "generating"

    assert rows(settings.database_path, PART_ROWS) == before
    assert ready == [PartsReady(meeting_id=meeting_id, run_id=_state(settings)[2])]


def test_previous_parts_that_no_longer_fit_go_to_needs_split(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    prepare: Prepare,
    ready: list[Event],
    status: str,
) -> None:
    """`transcript-split` 21 e 38: entrar em `needs_split` não apaga as Partes."""
    meeting_id = _divided(idle, settings, uow, status)
    longest, second, _ = _sizes(uow, meeting_id)
    assert use_budget(settings, uow, meeting_id, longest) < second
    before = rows(settings.database_path, PART_ROWS)

    assert prepare(meeting_id) == "needs_split"

    assert _state(settings)[:2] == ("needs_split", "too_long")
    assert rows(settings.database_path, PART_ROWS) == before
    assert ready == []


def test_adjust_in_done_goes_to_needs_split_even_if_parts_fit(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 22: `reajustar` não reaproveita; `split_reason` `adjust`."""
    meeting_id = _divided(idle, settings, uow, "done")
    _, second, whole = _sizes(uow, meeting_id)
    assert use_budget(settings, uow, meeting_id, second) < whole
    old_run = _state(settings)[2]

    assert prepare(meeting_id, "reajustar") == "needs_split"

    assert _state(settings) == ("needs_split", "adjust", old_run)
    assert _ranges(uow, meeting_id) == SPLIT
    assert ready == []


def test_adjust_with_whole_fitting_goes_on_with_single_part(
    idle: TestClient, settings: Settings, uow: Uow, prepare: Prepare, ready: list[Event]
) -> None:
    """`transcript-split` 22 (Q65): cabe inteira, segue sem tela."""
    meeting_id = _divided(idle, settings, uow, "done")
    use_budget(settings, uow, meeting_id, _sizes(uow, meeting_id)[2])

    assert prepare(meeting_id, "reajustar") == "generating"

    assert _ranges(uow, meeting_id) == [(0, 2)]
    assert len(ready) == 1
