import sqlite3
from pathlib import Path

import pytest

from snook.core.db import upgrade_database
from snook.modules.participants.models import Participant, SpeakerLink
from tests.auth.helpers import rows
from tests.meetings.test_storage_model import MEETING_ID, _insert_meeting, _insert_user


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "snook.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        _insert_user(conn)
        _insert_meeting(conn, status="transcribed")
    return path


def _connect(db: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db)
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _add(conn: sqlite3.Connection, name: str = "Ana", name_norm: str = "ana") -> int:
    cursor = conn.execute(
        "INSERT INTO participants (meeting_id, name, name_norm) VALUES (?, ?, ?)",
        (MEETING_ID, name, name_norm),
    )
    assert cursor.lastrowid is not None
    return cursor.lastrowid


def _link(conn: sqlite3.Connection, label: str, participant_id: int) -> None:
    conn.execute(
        "INSERT INTO speaker_links (meeting_id, speaker_label, participant_id) VALUES (?, ?, ?)",
        (MEETING_ID, label, participant_id),
    )


def test_tables_have_data_model_columns(db: Path) -> None:
    for table, model in (("participants", Participant), ("speaker_links", SpeakerLink)):
        columns = {row[1] for row in rows(db, f"PRAGMA table_info({table})")}
        assert {c.name for c in model.__table__.columns} == columns
    assert {row[1] for row in rows(db, "PRAGMA table_info(speaker_links)")} == {
        "meeting_id",
        "speaker_label",
        "participant_id",
    }


def test_meeting_delete_cascades(db: Path) -> None:
    with _connect(db) as conn:
        _link(conn, "SPEAKER_00", _add(conn))
        conn.execute("DELETE FROM meetings")
    assert rows(db, "SELECT COUNT(*) FROM participants") == [(0,)]
    assert rows(db, "SELECT COUNT(*) FROM speaker_links") == [(0,)]


def test_participant_delete_cascades_to_links(db: Path) -> None:
    with _connect(db) as conn:
        participant_id = _add(conn)
        _link(conn, "SPEAKER_00", participant_id)
        conn.execute("DELETE FROM participants")
    assert rows(db, "SELECT COUNT(*) FROM speaker_links") == [(0,)]


def test_speaker_links_to_one_participant(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _link(conn, "SPEAKER_00", _add(conn))
        _link(conn, "SPEAKER_00", _add(conn, "Bia", "bia"))


def test_name_norm_unique_per_meeting(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _add(conn)
        _add(conn, "ANA", "ana")


@pytest.mark.parametrize("name", ["", "x" * 101])
def test_name_length_checked(db: Path, name: str) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _add(conn, name, name)


def test_name_of_100_accepted(db: Path) -> None:
    with _connect(db) as conn:
        _add(conn, "x" * 100, "x" * 100)
    assert rows(db, "SELECT length(name) FROM participants") == [(100,)]


def test_link_needs_existing_participant(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), _connect(db) as conn:
        _link(conn, "SPEAKER_00", 999)
