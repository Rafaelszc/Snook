import sqlite3
import subprocess
import sys
import threading
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from snook.core.db import create_db_engine, create_session_factory, upgrade_database
from snook.modules.diarized_transcription import messages, repository
from snook.modules.diarized_transcription.engines.base import LANGUAGE, EngineFailure
from snook.modules.diarized_transcription.engines.fakes import CHUNKS, TURNS, fake_engines
from snook.modules.diarized_transcription.merge import Segment
from snook.modules.diarized_transcription.models import TranscriptSegment
from tests.auth.helpers import rows

MEETING_ID = "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
NOW = "2026-10-23T12:00:00Z"
COLUMNS = {"id", "meeting_id", "position", "speaker_label", "start_seconds", "end_seconds", "text"}
SEGMENTS = [Segment("SPEAKER_01", 5.0, 9.0, "depois"), Segment("SPEAKER_00", 0.0, 4.0, "antes")]


@pytest.fixture
def db(tmp_path: Path) -> Path:
    path = tmp_path / "snook.db"
    upgrade_database(path)
    with sqlite3.connect(path) as conn:
        conn.execute(
            "INSERT INTO users VALUES ('u1', 'u1@x.com', 'u1@x.com', 'u1', 'u1', 'hash', ?)",
            (NOW,),
        )
        conn.execute(
            "INSERT INTO meetings (id, user_id, title, original_filename, file_ext, "
            "duration_seconds, size_bytes, status, run_id, created_at, updated_at) "
            "VALUES (?, 'u1', 't', 'a.mp3', 'mp3', 60, 10, 'processing', 'r1', ?, ?)",
            (MEETING_ID, NOW, NOW),
        )
    return path


@pytest.fixture
def session(db: Path) -> Session:
    engine = create_db_engine(db)
    return create_session_factory(engine)()


def test_table_has_data_model_columns(db: Path) -> None:
    columns = {row[1] for row in rows(db, "PRAGMA table_info(transcript_segments)")}
    assert columns == COLUMNS
    assert {c.name for c in TranscriptSegment.__table__.columns} == COLUMNS


def test_segments_keep_given_order_by_position(session: Session) -> None:
    repository.add_segments(session, MEETING_ID, SEGMENTS)
    session.commit()

    stored = repository.list_segments(session, MEETING_ID)

    assert [(s.position, s.speaker_label, s.text) for s in stored] == [
        (0, "SPEAKER_01", "depois"),
        (1, "SPEAKER_00", "antes"),
    ]


def test_delete_segments_removes_only_that_meeting(session: Session) -> None:
    repository.add_segments(session, MEETING_ID, SEGMENTS)
    repository.delete_segments(session, MEETING_ID)
    session.commit()
    assert repository.list_segments(session, MEETING_ID) == []


def test_meeting_delete_cascades_to_segments(db: Path, session: Session) -> None:
    repository.add_segments(session, MEETING_ID, SEGMENTS)
    session.commit()
    with sqlite3.connect(db) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("DELETE FROM meetings")
    assert rows(db, "SELECT COUNT(*) FROM transcript_segments") == [(0,)]


def test_position_is_unique_per_meeting(db: Path, session: Session) -> None:
    repository.add_segments(session, MEETING_ID, SEGMENTS[:1])
    session.commit()
    with pytest.raises(sqlite3.IntegrityError), sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO transcript_segments (meeting_id, position, speaker_label, "
            "start_seconds, end_seconds, text) VALUES (?, 0, 'SPEAKER_00', 0, 1, 'x')",
            (MEETING_ID,),
        )


def test_segment_needs_existing_meeting(db: Path) -> None:
    with pytest.raises(sqlite3.IntegrityError), sqlite3.connect(db) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            "INSERT INTO transcript_segments (meeting_id, position, speaker_label, "
            "start_seconds, end_seconds, text) VALUES ('ghost', 0, 'SPEAKER_00', 0, 1, 'x')"
        )


def _source(tmp_path: Path) -> Path:
    source = tmp_path / MEETING_ID / "original.mp3"
    source.parent.mkdir()
    source.write_bytes(b"audio")
    return source


def test_fakes_succeed(tmp_path: Path) -> None:
    engines = fake_engines()
    target = tmp_path / "treated.flac"

    engines.audio.treat(_source(tmp_path), target, 10.0)

    assert target.exists()
    assert engines.diarizer.diarize(target, 3) == TURNS
    assert engines.transcriber.transcribe(target, LANGUAGE) == CHUNKS
    assert engines.diarizer.calls == [3]
    assert engines.transcriber.languages == ["pt"]


@pytest.mark.parametrize(
    ("outcome", "stage", "message"),
    [
        ("audio_failure", "audio", messages.AUDIO_FAILED),
        ("diarization_failure", "diarizer", messages.DIARIZATION_FAILED),
        ("transcription_failure", "transcriber", messages.TRANSCRIPTION_FAILED),
        ("hf_token", "diarizer", messages.HF_ACCESS_DENIED),
    ],
)
def test_fakes_fail(tmp_path: Path, outcome: str, stage: str, message: str) -> None:
    engines = fake_engines(outcome)  # type: ignore[arg-type]
    calls = {
        "audio": lambda: engines.audio.treat(_source(tmp_path), tmp_path / "t.flac", 10.0),
        "diarizer": lambda: engines.diarizer.diarize(tmp_path / "t.flac", None),
        "transcriber": lambda: engines.transcriber.transcribe(tmp_path / "t.flac", LANGUAGE),
    }
    with pytest.raises(EngineFailure) as caught:
        calls[stage]()
    assert caught.value.message == message


def test_hf_token_message_cites_token_and_terms() -> None:
    assert "HF_TOKEN" in messages.HF_ACCESS_DENIED
    assert "termos" in messages.HF_ACCESS_DENIED


def test_fake_no_speech_returns_no_chunks(tmp_path: Path) -> None:
    assert fake_engines("no_speech").transcriber.transcribe(tmp_path, LANGUAGE) == []


def test_held_fake_finishes_only_after_release(tmp_path: Path) -> None:
    engines = fake_engines(hold=True)
    source = _source(tmp_path)
    target = tmp_path / "treated.flac"
    worker = threading.Thread(target=engines.audio.treat, args=(source, target, 10.0))
    worker.start()

    assert engines.audio.wait_started(MEETING_ID)
    worker.join(0.05)
    assert worker.is_alive()
    assert not target.exists()

    engines.audio.release(MEETING_ID)
    worker.join(5)
    assert not worker.is_alive()
    assert target.exists()


def test_app_and_fakes_load_without_model_libraries() -> None:
    """Transversal 18, RT-13: a suíte padrão não importa engine de modelo nem GPU."""
    code = (
        "import sys, snook.main, snook.modules.diarized_transcription.engines.fakes\n"
        "heavy = {'torch', 'faster_whisper', 'pyannote', 'ctranslate2'} & set(sys.modules)\n"
        "assert not heavy, heavy\n"
    )
    subprocess.run([sys.executable, "-c", code], check=True)  # noqa: S603
