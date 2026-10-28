import sqlite3
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import service
from snook.modules.backlog_generation.merge import merge_backlogs
from snook.modules.backlog_generation.validation import parse_backlog
from snook.modules.participants import service as participants
from tests.auth.helpers import rows
from tests.backlog_generation.helpers import DURATION, backlog, count, story
from tests.diarized_transcription.helpers import create
from tests.transcript_split.helpers import confirmed

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
TABLES = ("epics", "user_stories", "acceptance_criteria", "backlog_counters")


def _save(uow: Uow, meeting_id: str, raw: str) -> None:
    with uow() as unit:
        epics = merge_backlogs(
            [parse_backlog(raw, duration_seconds=DURATION)],
            participants.list_participants(unit, meeting_id),
        )
        service.backlog(unit).replace(meeting_id, epics)


THREE = backlog(("Cadastro", [story("A", criteria=2), story("B"), story("C")]))


def test_backlog_goes_with_meeting(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """04-data-model: `ON DELETE CASCADE` da Reunião leva Epics, US, critérios e contador."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, THREE)
    assert [count(settings, table) for table in TABLES] == [1, 3, 4, 1]

    assert idle.delete(f"/api/meetings/{meeting_id}").status_code == 204

    assert [count(settings, table) for table in TABLES] == [0, 0, 0, 0]


def test_requester_set_null_is_only_a_safety_net(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """04-data-model: Participante apagado por fora deixa o solicitante vazio, sem apagar a US."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, THREE)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM speaker_links WHERE meeting_id = ?", (meeting_id,))
        conn.execute("DELETE FROM participants WHERE name = 'Ana'")

    assert rows(settings.database_path, "SELECT requested_by FROM user_stories") == [(None,)] * 3


def test_next_us_number_after_largest(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """`next_us_number`: sem backlog, 1; depois do maior existente; reserva o número devolvido."""
    meeting_id = confirmed(idle, settings)
    with uow() as unit:
        assert service.next_us_number(unit, meeting_id) == 1
    _save(uow, meeting_id, THREE)

    with uow() as unit:
        assert service.next_us_number(unit, meeting_id) == 4
        assert service.next_us_number(unit, meeting_id) == 5


def test_next_us_number_skips_deleted_largest(
    idle: TestClient, settings: Settings, uow: Uow
) -> None:
    """`backlog-review` 19: excluir a maior US não devolve o número dela."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, THREE)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("DELETE FROM user_stories WHERE us_number = 3")

    with uow() as unit:
        assert service.next_us_number(unit, meeting_id) == 4


def test_replace_restarts_numbering(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """Q50: substituir o backlog zera o contador; a criação manual segue do novo maior."""
    meeting_id = confirmed(idle, settings)
    _save(uow, meeting_id, THREE)
    with uow() as unit:
        service.next_us_number(unit, meeting_id)

    _save(uow, meeting_id, backlog(("Outra", [story("D")])))

    with uow() as unit:
        assert [s.us_number for s in service.backlog(unit).stories(meeting_id)] == [1]
        assert service.next_us_number(unit, meeting_id) == 2


def test_backlog_of_other_meeting_untouched(idle: TestClient, settings: Settings, uow: Uow) -> None:
    """Substituir o backlog de uma Reunião não mexe no de outra."""
    first = confirmed(idle, settings)
    second = create(idle)
    _save(uow, first, THREE)

    _save(uow, second, backlog(("Cadastro", [story("X")])))

    with uow() as unit:
        assert [s.name for s in service.backlog(unit).stories(first)] == ["A", "B", "C"]
        assert [s.name for s in service.backlog(unit).stories(second)] == ["X"]
