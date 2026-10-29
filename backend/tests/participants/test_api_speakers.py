import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from tests.auth.helpers import Users
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields
from tests.participants.conftest import add_segments

pytestmark = pytest.mark.usefixtures("probe", "clock")

SEGMENTS = [
    ("SPEAKER_00", 0.0, 4.0),
    ("SPEAKER_01", 4.0, 6.5),
    ("SPEAKER_00", 6.5, 8.0),
]


def _url(meeting_id: str) -> str:
    return f"/api/meetings/{meeting_id}/speakers"


@pytest.mark.parametrize("status", ["transcribed", "needs_split", "generating", "done"])
def test_each_speaker_once_with_total_seconds(
    idle: TestClient, settings: Settings, status: str
) -> None:
    """`participants` 1."""
    meeting_id = create(idle)
    add_segments(settings, meeting_id, SEGMENTS)
    set_fields(settings.database_path, meeting_id, status=status)

    response = idle.get(_url(meeting_id))

    assert response.status_code == 200
    assert response.json() == [
        {"speaker_label": "SPEAKER_00", "total_seconds": pytest.approx(5.5)},
        {"speaker_label": "SPEAKER_01", "total_seconds": pytest.approx(2.5)},
    ]


def test_failed_in_generation_still_lists(idle: TestClient, settings: Settings) -> None:
    meeting_id = create(idle)
    add_segments(settings, meeting_id, SEGMENTS)
    set_fields(
        settings.database_path,
        meeting_id,
        status="failed",
        failed_stage="generation",
        error_message="x",
    )

    assert len(idle.get(_url(meeting_id)).json()) == 2


@pytest.mark.parametrize(
    "fields",
    [
        {"status": "pending"},
        {"status": "processing"},
        {"status": "failed", "failed_stage": "transcription", "error_message": "x"},
    ],
)
def test_before_transcribed_is_409(
    idle: TestClient, settings: Settings, fields: dict[str, str]
) -> None:
    """`05-api.md`: 409 fora de `transcribed` e posteriores."""
    meeting_id = create(idle)
    set_fields(settings.database_path, meeting_id, **fields)

    response = idle.get(_url(meeting_id))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "speakers_not_ready"


def test_other_users_meeting_is_404(idle: TestClient, settings: Settings, users: Users) -> None:
    """`participants` 23; SEC-02."""
    meeting_id = create(idle)
    add_segments(settings, meeting_id, SEGMENTS)
    set_fields(settings.database_path, meeting_id, status="transcribed")
    users.use("bia")

    response = idle.get(_url(meeting_id))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"


def test_without_session_is_401(client: TestClient) -> None:
    """`participants` 24; SEC-01."""
    assert client.get(_url("00000000-0000-0000-0000-000000000000")).status_code == 401
