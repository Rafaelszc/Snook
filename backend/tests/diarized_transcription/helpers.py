import hashlib
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from tests.auth.helpers import rows
from tests.meetings.helpers import upload


def create(client: TestClient, **data: Any) -> str:
    response = upload(client, **data)
    assert response.status_code == 201
    meeting_id: str = response.json()["id"]
    return meeting_id


def state(db: Path, meeting_id: str) -> tuple[Any, ...]:
    [row] = rows(
        db,
        f"SELECT status, failed_stage, error_message FROM meetings WHERE id = '{meeting_id}'",  # noqa: S608
    )
    return row


def segments(db: Path, meeting_id: str) -> list[tuple[Any, ...]]:
    return rows(
        db,
        "SELECT position, speaker_label, start_seconds, end_seconds, text "  # noqa: S608
        f"FROM transcript_segments WHERE meeting_id = '{meeting_id}' ORDER BY position",
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
