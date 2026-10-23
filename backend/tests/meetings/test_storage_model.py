import sqlite3
from pathlib import Path
from typing import Any

import pytest
from alembic import command
from alembic.config import Config

from snook.core.db import upgrade_database
from snook.modules.meetings import schemas
from snook.modules.meetings.models import Meeting
from tests.auth.helpers import rows

_ALEMBIC = Path(__file__).resolve().parents[2] / "alembic"
MEETING_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
NOW = "2026-10-23T12:00:00Z"


def _insert_user(conn: sqlite3.Connection, user_id: str = "u1") -> None:
    conn.execute(
        "INSERT INTO users VALUES (?, ?, ?, ?, ?, 'hash', ?)",
        (user_id, f"{user_id}@x.com", f"{user_id}@x.com", user_id, user_id, NOW),
    )


def _meeting(**overrides: Any) -> dict[str, Any]:
    values: dict[str, Any] = {
        "id": MEETING_ID,
        "user_id": "u1",
        "title": "Planejamento",
        "original_filename": "planejamento.mp3",
        "file_ext": "mp3",
        "duration_seconds": 60.0,
        "size_bytes": 1000,
        "expected_speakers": None,
        "status": "pending",
        "failed_stage": None,
        "error_message": None,
        "split_reason": None,
        "run_id": "r1",
        "participants_confirmed_at": None,
        "backlog_saved_at": None,
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    return values


def _insert_meeting(conn: sqlite3.Connection, **overrides: Any) -> None:
    values = _meeting(**overrides)
    columns = ", ".join(values)
    marks = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO meetings ({columns}) VALUES ({marks})", list(values.values()))  # noqa: S608


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "snook.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        _insert_user(conn)
    return path


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def test_table_has_data_model_columns(db: Path) -> None:
    columns = {row[1] for row in rows(db, "PRAGMA table_info(meetings)")}
    assert columns == set(_meeting())
    assert {c.name for c in Meeting.__table__.columns} == columns


def test_user_delete_cascades_to_meetings(db: Path) -> None:
    with _connect(db) as conn:
        _insert_meeting(conn)
        conn.execute("DELETE FROM users WHERE id = 'u1'")
    assert rows(db, "SELECT COUNT(*) FROM meetings") == [(0,)]


def test_meeting_needs_existing_user(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _insert_meeting(conn, user_id="ghost")


@pytest.mark.parametrize(
    "overrides",
    [
        {"status": "unknown"},
        {"status": "failed"},
        {"status": "failed", "failed_stage": "transcription"},
        {"status": "failed", "error_message": "erro"},
        {"failed_stage": "upload"},
        {"file_ext": "flac"},
        {"expected_speakers": 0},
        {"expected_speakers": 21},
        {"duration_seconds": 0},
        {"duration_seconds": 7200.5},
        {"size_bytes": 524288001},
        {"title": ""},
        {"title": "x" * 201},
        {"split_reason": "other"},
    ],
)
def test_checks_refuse_invalid_rows(db: Path, overrides: dict[str, Any]) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _insert_meeting(conn, **overrides)


def test_checks_accept_limits(db: Path) -> None:
    with _connect(db) as conn:
        _insert_meeting(
            conn,
            status="failed",
            failed_stage="generation",
            error_message="processamento interrompido",
            expected_speakers=20,
            duration_seconds=7200,
            size_bytes=524288000,
            title="x" * 200,
        )
    assert rows(db, "SELECT status FROM meetings") == [("failed",)]


def test_output_schemas_have_no_file_path() -> None:
    """`meetings` 21: nenhum schema de saída traz caminho ou extensão interna."""
    for model in (schemas.MeetingOut,):
        assert not {name for name in model.model_fields if "path" in name or "file_ext" in name}


def test_upgrade_head_runs_over_llm_providers_database(tmp_path: Path) -> None:
    """Banco no head da Task 12.2 (0002), com dados, sobe para o head sem perder nada."""
    path = tmp_path / "old.db"
    config = Config()
    config.set_main_option("script_location", str(_ALEMBIC))
    config.attributes["database_path"] = path
    command.upgrade(config, "0002")
    with sqlite3.connect(path) as conn:
        _insert_user(conn)
        conn.execute(
            "INSERT INTO llm_configs (user_id, provider, model, context_window, key_status, "
            "is_active, created_at, updated_at) VALUES ('u1', 'ollama', 'm', 8192, 'ok', 1, ?, ?)",
            (NOW, NOW),
        )
    upgrade_database(path)
    assert rows(path, "SELECT version_num FROM alembic_version") == [("0004",)]
    assert rows(path, "SELECT provider FROM llm_configs") == [("ollama",)]
    with _connect(path) as conn:
        _insert_meeting(conn)
    assert rows(path, "SELECT id FROM meetings") == [(MEETING_ID,)]
