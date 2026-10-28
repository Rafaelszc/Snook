import sqlite3
from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.backlog_generation import runner
from snook.modules.llm_providers.service import ProviderUnreachable
from snook.modules.meetings import service as meetings
from tests.auth.helpers import rows
from tests.backlog_generation.helpers import (
    FakeGenerate,
    backlog,
    count,
    generating,
    parts_ready,
    regenerating,
    stored_stories,
    story,
)
from tests.diarized_transcription.helpers import state

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]
THREE_PARTS = [(0, 0), (1, 1), (2, 2)]
TABLES = ("epics", "user_stories", "acceptance_criteria")


def _has_backlog(uow: Uow, meeting_id: str) -> bool:
    with uow() as unit:
        return meetings.read_flags(unit, meeting_id).has_backlog


def _failed_generation(settings: Settings, meeting_id: str) -> None:
    status, stage, message = state(settings.database_path, meeting_id)
    assert (status, stage) == ("failed", "generation")
    assert message


def test_saved_field_by_field(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 7, 34: cada campo gravado, critérios na ordem, marca registrada."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [
        backlog(
            (
                " Cadastro ",
                [story("Cadastrar", requested_by="bia", requested_at="01:02:03", criteria=2)],
            )
        )
    ]

    parts_ready(idle, meeting_id)

    [(bia_id,)] = rows(settings.database_path, "SELECT id FROM participants WHERE name = 'Bia'")
    assert rows(settings.database_path, "SELECT name, position FROM epics") == [("Cadastro", 1)]
    assert rows(
        settings.database_path,
        "SELECT us_number, name, as_a, i_want, so_that, priority, story_points, requested_by, "
        "requested_at_seconds, position FROM user_stories",
    ) == [
        (
            1,
            "Cadastrar",
            "atendente",
            "cadastrar com CPF",
            "eu possa abrir pedidos",
            "High",
            5,
            bia_id,
            3723,
            1,
        )
    ]
    assert rows(
        settings.database_path,
        "SELECT given, when_, then_, position FROM acceptance_criteria ORDER BY position",
    ) == [("dado 1", "quando 1", "então 1", 1), ("dado 2", "quando 2", "então 2", 2)]
    assert _has_backlog(uow, meeting_id)


def test_failure_in_part_two_saves_nothing(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 22, 34: nada das Partes 1 e 2, Parte 3 não chamada, sem marca."""
    meeting_id = generating(idle, settings, uow, THREE_PARTS)
    generate.replies = [backlog(("Cadastro", [story()])), ProviderUnreachable("timeout")]

    parts_ready(idle, meeting_id)

    assert len(generate.calls) == 2
    _failed_generation(settings, meeting_id)
    assert [count(settings, table) for table in TABLES] == [0, 0, 0]
    assert not _has_backlog(uow, meeting_id)


def test_error_mid_save_leaves_nothing(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`backlog-generation` 25; SEC-19: erro no meio da gravação desfaz tudo, sem status preso."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]

    def broken(*_args: object, **_kwargs: object) -> None:
        raise RuntimeError("disco cheio")

    monkeypatch.setattr(runner.meetings, "mark_backlog_saved", broken)

    parts_ready(idle, meeting_id)

    _failed_generation(settings, meeting_id)
    assert [count(settings, table) for table in TABLES] == [0, 0, 0]


def test_regeneration_replaces_edited_backlog(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 23: o novo backlog substitui o anterior, com edições, de `US-01`."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story("A"), story("B")]))]
    parts_ready(idle, meeting_id)
    with sqlite3.connect(settings.database_path) as conn:
        conn.execute("UPDATE user_stories SET name = 'Editada' WHERE us_number = 1")
        conn.execute("DELETE FROM user_stories WHERE us_number = 2")

    regenerating(settings, meeting_id, "run-2")
    generate.replies = [backlog(("Busca", [story("C"), story("D")]))]
    parts_ready(idle, meeting_id, "run-2")

    assert state(settings.database_path, meeting_id) == ("done", None, None)
    assert stored_stories(settings, meeting_id) == [(1, "Busca", "C"), (2, "Busca", "D")]
    assert count(settings, "epics") == 1


def test_failed_regeneration_keeps_previous(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """`backlog-generation` 24: regeneração que falha mantém o backlog anterior intacto."""
    meeting_id = generating(idle, settings, uow, [(0, 1), (2, 2)])
    generate.replies = [backlog(("Cadastro", [story("A")])), backlog(("Busca", [story("B")]))]
    parts_ready(idle, meeting_id)
    before = stored_stories(settings, meeting_id)

    regenerating(settings, meeting_id, "run-2")
    generate.replies = [backlog(("Outra", [story("C")])), "não é JSON"]
    parts_ready(idle, meeting_id, "run-2")

    _failed_generation(settings, meeting_id)
    assert stored_stories(settings, meeting_id) == before
    assert before == [(1, "Cadastro", "A"), (2, "Busca", "B")]


def test_deleted_meeting_saves_nothing(
    idle: TestClient, settings: Settings, uow: Uow, generate: FakeGenerate
) -> None:
    """Reunião excluída durante a geração: a gravação final não grava nada."""
    meeting_id = generating(idle, settings, uow)
    generate.replies = [backlog(("Cadastro", [story()]))]
    generate.on_call = lambda _call: idle.delete(f"/api/meetings/{meeting_id}")

    parts_ready(idle, meeting_id)

    assert [count(settings, table) for table in TABLES] == [0, 0, 0]
