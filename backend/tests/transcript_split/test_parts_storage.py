from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers.service import ActiveProvider
from snook.modules.transcript_split import service
from tests.auth.helpers import rows
from tests.transcript_split.helpers import SEGMENTS, FakeEstimate, confirmed

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
SNAPSHOT = ActiveProvider(provider="ollama", model="llama3", context_window=100_000)


def _save(uow: Uow, meeting_id: str, ranges: list[tuple[int, int]]) -> None:
    with uow() as unit:
        service.save_parts(unit, SNAPSHOT, meeting_id, ranges, estimate=FakeEstimate())


def _parts(uow: Uow, meeting_id: str) -> list[service.Part]:
    with uow() as unit:
        return service.list_parts(unit, meeting_id)


def test_save_replaces_previous_parts(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 37: Parte única troca a divisão anterior; "Partes" só devolve as novas."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, [(0, 0), (1, 2)])

    _save(uow, meeting_id, [(0, 2)])

    parts = _parts(uow, meeting_id)
    assert [(p.index, p.first, p.last) for p in parts] == [(1, 0, 2)]
    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(1,)]


def test_failed_save_keeps_previous_parts(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 37: apagar e gravar na mesma transação; erro desfaz os dois."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, [(0, 0), (1, 2)])

    with pytest.raises(IndexError), uow() as unit:
        service.save_parts(unit, SNAPSHOT, meeting_id, [(0, 9)], estimate=FakeEstimate())

    assert [(p.first, p.last) for p in _parts(uow, meeting_id)] == [(0, 0), (1, 2)]


def test_parts_persist_without_new_save(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`transcript-split` 38: leitura não regrava; ids das linhas continuam."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, [(0, 1), (2, 2)])
    before = rows(settings.database_path, "SELECT id FROM transcript_parts ORDER BY id")

    _parts(uow, meeting_id)

    assert rows(settings.database_path, "SELECT id FROM transcript_parts ORDER BY id") == before


def test_parts_store_absolute_bounds_and_text(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`transcript-split` 18: início do primeiro e fim do último segmento, absolutos."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, [(0, 0), (1, 2)])

    first, second = _parts(uow, meeting_id)

    assert (first.start_seconds, first.end_seconds) == (SEGMENTS[0][1], SEGMENTS[0][2])
    assert (second.start_seconds, second.end_seconds) == (SEGMENTS[1][1], SEGMENTS[2][2])
    with uow() as unit:
        assert second.text == service.part_text(unit, meeting_id, 1, 2)
    assert second.estimated_tokens == len(second.text)


def test_parts_go_with_meeting(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """Exclusão: Partes somem com a Reunião (cascata)."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, [(0, 2)])

    assert idle.delete(f"/api/meetings/{meeting_id}").status_code == 204

    assert rows(settings.database_path, "SELECT count(*) FROM transcript_parts") == [(0,)]
