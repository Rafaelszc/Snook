# ruff: noqa: F811
import sqlite3
from collections.abc import Callable
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.auth import service as auth
from snook.modules.meetings import service as meetings
from tests.auth.helpers import Users, rows
from tests.backlog_generation.conftest import generate  # noqa: F401
from tests.backlog_generation.helpers import FakeGenerate, story
from tests.backlog_review.helpers import backlog_url, with_backlog
from tests.meetings.conftest import ana, clock, probe, uow, users  # noqa: F401
from tests.meetings.helpers import upload
from tests.participants.conftest import activate_provider, idle  # noqa: F401

pytestmark = pytest.mark.usefixtures("probe", "clock")

Uow = Callable[[], UnitOfWork]


def _user_id(db: Path, username: str) -> str:
    return str(rows(db, f"SELECT id FROM users WHERE username = '{username}'")[0][0])  # noqa: S608


def _tables(db: Path) -> list[str]:
    found = rows(db, "SELECT name FROM sqlite_master WHERE type = 'table'")
    return [name for (name,) in found if name not in ("alembic_version", "sqlite_sequence")]


def _dump(db: Path) -> dict[str, set[tuple[object, ...]]]:
    return {table: set(rows(db, f"SELECT * FROM {table}")) for table in _tables(db)}  # noqa: S608


@pytest.mark.parametrize("typed", ["ana", "ANA", "  Ana  "])
def test_find_user_by_username_ignores_case(
    idle: TestClient, settings: Settings, uow: Uow, typed: str
) -> None:
    """Q39; SEC-24: compara por `username_norm`."""
    with uow() as u:
        found = auth.find_user_by_username(u, typed)

    assert found is not None
    assert found.id == _user_id(settings.database_path, "ana")
    assert found.username == "ana"


def test_find_user_by_username_does_not_match_email(idle: TestClient, uow: Uow) -> None:
    """Só nome de usuário: email não acha (`02-architecture.md`, "Exclusão de Usuário")."""
    with uow() as u:
        assert auth.find_user_by_username(u, "ana@x.com") is None
        assert auth.find_user_by_username(u, "carla") is None


def test_delete_user_cascades_everything_of_that_user(
    idle: TestClient,
    settings: Settings,
    uow: Uow,
    generate: FakeGenerate,  # noqa: F811
    users: Users,
) -> None:
    """SEC-24: um commit leva sessões, LLM, Reuniões e derivados; outro Usuário não muda."""
    db = settings.database_path
    ana_meeting = with_backlog(idle, settings, uow, generate, ("Cadastro", [story(criteria=2)]))
    users.use("bia")
    activate_provider(settings, "bia")
    bia_meeting = with_backlog(idle, settings, uow, generate, ("Vendas", [story("Vender")]))
    bia_backlog = idle.get(backlog_url(bia_meeting)).json()
    ana_id = _user_id(db, "ana")
    before = _dump(db)

    with uow() as u:
        ids = meetings.list_meeting_ids_for_user(u, ana_id)
        auth.delete_user(u, ana_id)

    assert ids == [ana_meeting]
    after = _dump(db)
    for table, remaining in after.items():
        assert remaining <= before[table], table
        flat = {str(value) for row in remaining for value in row}
        assert ana_id not in flat and ana_meeting not in flat, table
    for table in (
        "users",
        "sessions",
        "llm_configs",
        "meetings",
        "transcript_segments",
        "participants",
        "epics",
        "user_stories",
        "acceptance_criteria",
    ):
        assert len(after[table]) < len(before[table]), table
    with sqlite3.connect(db) as conn:
        assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    assert idle.get(backlog_url(bia_meeting)).json() == bia_backlog


def test_list_meeting_ids_only_of_that_user(
    idle: TestClient, settings: Settings, uow: Uow, users: Users
) -> None:
    first = upload(idle).json()["id"]
    second = upload(idle).json()["id"]
    users.use("bia")
    upload(idle)

    with uow() as u:
        ids = meetings.list_meeting_ids_for_user(u, _user_id(settings.database_path, "ana"))

    assert sorted(ids) == sorted([first, second])
