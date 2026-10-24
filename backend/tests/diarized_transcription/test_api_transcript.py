import sqlite3

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.auth.helpers import Users
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields

pytestmark = pytest.mark.usefixtures("probe", "clock")


def _add_segments(settings: Settings, meeting_id: str) -> None:
    with sqlite3.connect(settings.database_path) as conn:
        conn.executemany(
            "INSERT INTO transcript_segments "
            "(meeting_id, position, speaker_label, start_seconds, end_seconds, text) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            [
                (meeting_id, 1, "SPEAKER_01", 5.5, 9.5, "Segundo."),
                (meeting_id, 0, "SPEAKER_00", 0.5, 4.5, "Primeiro."),
            ],
        )


def _url(meeting_id: str) -> str:
    return f"/api/meetings/{meeting_id}/transcript"


@pytest.fixture
def idle(ana: TestClient) -> TestClient:
    """Sem consumidor: a Reunião fica como o teste a deixar."""
    app: FastAPI = ana.app  # type: ignore[assignment]
    app.state.transcription.stop()
    return ana


@pytest.mark.parametrize("status", ["transcribed", "generating", "needs_split", "done"])
def test_transcript_returns_segments_in_order(
    idle: TestClient, settings: Settings, status: str
) -> None:
    """`diarized-transcription` 18."""
    meeting_id = create(idle)
    _add_segments(settings, meeting_id)
    set_fields(settings.database_path, meeting_id, status=status)

    response = idle.get(_url(meeting_id))

    assert response.status_code == 200
    segments = response.json()["segments"]
    assert [
        (s["speaker_label"], s["start_seconds"], s["end_seconds"], s["text"]) for s in segments
    ] == [
        ("SPEAKER_00", 0.5, 4.5, "Primeiro."),
        ("SPEAKER_01", 5.5, 9.5, "Segundo."),
    ]
    assert all(isinstance(s["id"], int) for s in segments)


def test_failed_in_generation_still_has_transcript(idle: TestClient, settings: Settings) -> None:
    meeting_id = create(idle)
    _add_segments(settings, meeting_id)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="x",
    )

    assert len(idle.get(_url(meeting_id)).json()["segments"]) == 2


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "pending"},
        {"status": "processing"},
        {"status": "failed", "failed_stage": "transcription", "error_message": "x"},
    ],
)
def test_transcript_not_ready_is_409(
    idle: TestClient, settings: Settings, fields: dict[str, str]
) -> None:
    """`diarized-transcription` 19."""
    meeting_id = create(idle)
    set_fields(settings.database_path, meeting_id, **fields)

    response = idle.get(_url(meeting_id))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "transcript_not_ready"


def test_other_users_meeting_is_404(idle: TestClient, settings: Settings, users: Users) -> None:
    """`diarized-transcription` 20; SEC-02."""
    meeting_id = create(idle)
    _add_segments(settings, meeting_id)
    set_fields(settings.database_path, meeting_id, status="transcribed")
    users.use("bia")

    response = idle.get(_url(meeting_id))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_unknown_meeting_is_404(ana: TestClient) -> None:
    assert ana.get(_url("00000000-0000-0000-0000-000000000000")).status_code == 404


def test_transcript_without_session_is_401(client: TestClient) -> None:
    assert client.get(_url("00000000-0000-0000-0000-000000000000")).status_code == 401
