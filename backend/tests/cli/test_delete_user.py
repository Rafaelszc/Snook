# ruff: noqa: F811
import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook import cli
from snook.core.runlock import RunLock
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from tests.auth.helpers import PASSWORD, Users, rows
from tests.backlog_generation.helpers import FakeGenerate, story
from tests.backlog_review.helpers import with_backlog
from tests.diarized_transcription.helpers import create
from tests.meetings.conftest import clock, probe  # noqa: F401
from tests.participants.conftest import activate_provider

pytestmark = pytest.mark.usefixtures("probe", "clock")


@dataclass
class World:
    db: Path
    audios: Path
    ana_meetings: list[str]
    bia_meeting: str


def _client(app: FastAPI) -> TestClient:
    return TestClient(app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"})


@pytest.fixture
def world(app: FastAPI, settings: Settings) -> World:
    """Ana (duas Reuniões, uma com backlog) e Bia (uma com backlog); backend parado no fim."""
    with _client(app) as client:
        app.state.prepare_generation = lambda event: None
        generate = FakeGenerate()
        app.state.generate = generate
        app.state.generate_backlog = app.state.generation.run
        uow: Callable[[], UnitOfWork] = lambda: UnitOfWork(  # noqa: E731
            app.state.session_factory, app.state.event_bus.publish
        )
        users = Users(client)
        users.add("bia")
        users.add("ana")
        ana_backlog = with_backlog(client, settings, uow, generate, ("Cadastro", [story()]))
        ana_plain = create(client)
        users.use("bia")
        activate_provider(settings, "bia")
        bia_meeting = with_backlog(client, settings, uow, generate, ("Vendas", [story("Vender")]))
    return World(settings.database_path, settings.audio_root, [ana_backlog, ana_plain], bia_meeting)


def _tables(db: Path) -> list[str]:
    found = rows(db, "SELECT name FROM sqlite_master WHERE type = 'table'")
    return [name for (name,) in found if name != "alembic_version"]


def _dump(db: Path) -> dict[str, list[tuple[object, ...]]]:
    return {t: sorted(rows(db, f"SELECT * FROM {t}"), key=repr) for t in _tables(db)}  # noqa: S608


def _ana_id(db: Path) -> str:
    return str(rows(db, "SELECT id FROM users WHERE username = 'ana'")[0][0])


def _login(app: FastAPI, identifier: str) -> int:
    with _client(app) as client:
        response = client.post(
            "/api/auth/login", json={"identifier": identifier, "password": PASSWORD}
        )
        return response.status_code


def test_deletes_user_rows_and_dirs_only(app: FastAPI, world: World) -> None:
    """SEC-24; transversal 21; US 25: tudo de Ana sai; Bia não muda; login de Ana 401."""
    ana_id = _ana_id(world.db)
    before = _dump(world.db)
    for meeting_id in [*world.ana_meetings, world.bia_meeting]:
        assert (world.audios / meeting_id).is_dir()

    assert cli.main(["delete-user", "ana", "--yes"]) == 0

    after = _dump(world.db)
    for table, remaining in after.items():
        assert set(remaining) <= set(before[table]), table
        flat = {str(value) for row in remaining for value in row}
        assert not flat & {ana_id, *world.ana_meetings}, table
    assert rows(world.db, "SELECT username FROM users") == [("bia",)]
    for meeting_id in world.ana_meetings:
        assert not (world.audios / meeting_id).exists()
    assert (world.audios / world.bia_meeting).is_dir()
    assert _login(app, "ana") == 401
    assert _login(app, "ana@x.com") == 401
    assert _login(app, "bia") == 200


def test_bia_data_unchanged(world: World) -> None:
    """SEC-24: linhas de outro Usuário ficam iguais."""
    query = f"SELECT * FROM epics WHERE meeting_id = '{world.bia_meeting}'"  # noqa: S608
    before = rows(world.db, query)

    assert cli.main(["delete-user", "ana", "--yes"]) == 0

    assert rows(world.db, query) == before
    assert rows(world.db, "SELECT COUNT(*) FROM meetings") == [(1,)]


@pytest.mark.parametrize("typed", ["ANA", "Ana"])
def test_finds_user_with_different_case(world: World, typed: str) -> None:
    """Q39: compara por `username_norm`."""
    assert cli.main(["delete-user", typed, "--yes"]) == 0

    assert rows(world.db, "SELECT username FROM users") == [("bia",)]


@pytest.mark.parametrize("name", ["carla", "ana@x.com"])
def test_unknown_user_exits_1_without_writing(
    world: World, name: str, capsys: pytest.CaptureFixture[str]
) -> None:
    """SEC-24: inexistente sai com 1, nada escrito. Email não serve de nome."""
    before = _dump(world.db)

    assert cli.main(["delete-user", name, "--yes"]) == 1

    assert _dump(world.db) == before
    assert "erro:" in capsys.readouterr().err


@pytest.mark.parametrize("name", ["a", "nome com espaço", "x" * 31, "ana;drop"])
def test_argument_goes_through_signup_validation(world: World, name: str) -> None:
    """`03-security.md`, superfícies: o argumento segue a regra do cadastro."""
    before = _dump(world.db)

    assert cli.main(["delete-user", name, "--yes"]) == 1

    assert _dump(world.db) == before


def test_wrong_confirmation_deletes_nothing(
    world: World, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """SEC-24; `08-deployment.md`, "CLI de escrita"."""
    before = _dump(world.db)
    monkeypatch.setattr("builtins.input", lambda _prompt: "bia")

    assert cli.main(["delete-user", "ana"]) == 1

    assert _dump(world.db) == before
    for meeting_id in world.ana_meetings:
        assert (world.audios / meeting_id).is_dir()
    assert "confirmação" in capsys.readouterr().err


def test_matching_confirmation_deletes(world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    prompts: list[str] = []
    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "ana")

    assert cli.main(["delete-user", "ana"]) == 0

    assert len(prompts) == 1
    assert rows(world.db, "SELECT username FROM users") == [("bia",)]


def test_busy_lock_stops_without_deleting(world: World, capsys: pytest.CaptureFixture[str]) -> None:
    """Abuse case "delete-user com backend no ar" (ADR-0006)."""
    before = _dump(world.db)

    with RunLock(world.db.with_name("snook.lock")):
        assert cli.main(["delete-user", "ana", "--yes"]) == 1

    assert _dump(world.db) == before
    for meeting_id in world.ana_meetings:
        assert (world.audios / meeting_id).is_dir()
    assert "snook.lock" in capsys.readouterr().err


def test_logs_user_id_and_count_without_email_or_username(
    world: World, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    """SEC-20; `07-observability.md`."""
    ana_id = _ana_id(world.db)
    caplog.set_level(logging.INFO)

    assert cli.main(["delete-user", "ana", "--yes"]) == 0

    [record] = [r for r in caplog.records if r.getMessage() == "operator.user_deleted"]
    assert record.__dict__["user_id"] == ana_id
    assert record.__dict__["meetings_count"] == 2
    captured = capsys.readouterr()
    logged = caplog.text + captured.err
    assert "ana@x.com" not in logged
    assert "'ana'" not in logged and '"ana"' not in logged
