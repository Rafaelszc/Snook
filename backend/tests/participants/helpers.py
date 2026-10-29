from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.auth.helpers import rows
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields
from tests.participants.conftest import add_segments

SEGMENTS = [
    ("SPEAKER_00", 0.0, 4.0),
    ("SPEAKER_01", 4.0, 6.5),
    ("SPEAKER_02", 6.5, 8.0),
]


def url(meeting_id: str) -> str:
    return f"/api/meetings/{meeting_id}/participants"


def transcribed(client: TestClient, settings: Settings) -> str:
    """Reunião em `transcribed` com três speakers."""
    meeting_id = create(client)
    add_segments(settings, meeting_id, SEGMENTS)
    set_fields(settings.database_path, meeting_id, status="transcribed")
    return meeting_id


def names(**overrides: str) -> dict[str, Any]:
    values = {"SPEAKER_00": "Ana", "SPEAKER_01": "Bia", "SPEAKER_02": "Caio"}
    values.update(overrides)
    return {"names": values}


def stored(db: Path) -> tuple[list[tuple[Any, ...]], list[tuple[Any, ...]]]:
    """Participantes `(name, name_norm)` e vínculos `(speaker_label, name)` gravados."""
    return (
        rows(db, "SELECT name, name_norm FROM participants ORDER BY id"),
        rows(
            db,
            "SELECT l.speaker_label, p.name FROM speaker_links l "
            "JOIN participants p ON p.id = l.participant_id ORDER BY l.speaker_label",
        ),
    )


def confirmed_at(db: Path, meeting_id: str) -> Any:
    [(value,)] = rows(
        db,
        f"SELECT participants_confirmed_at FROM meetings WHERE id = '{meeting_id}'",  # noqa: S608
    )
    return value
