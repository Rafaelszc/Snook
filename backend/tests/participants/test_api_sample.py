from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.modules.diarized_transcription import service as transcription
from tests.auth.helpers import Users
from tests.diarized_transcription.helpers import create
from tests.meetings.helpers import set_fields
from tests.participants.conftest import add_segments

pytestmark = pytest.mark.usefixtures("probe", "clock")

WAV = b"RIFF-fake-wav"


@pytest.fixture
def clips(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, float, float]]:
    """Fake do "Áudio tratado": guarda o intervalo pedido e devolve bytes fixos."""
    calls: list[tuple[str, float, float]] = []

    def fake(audio_root: Path, meeting_id: str, start: float, end: float) -> bytes:
        calls.append((meeting_id, start, end))
        return WAV

    monkeypatch.setattr(transcription, "treated_audio_clip", fake)
    return calls


def _meeting(
    client: TestClient, settings: Settings, segments: list[tuple[str, float, float]]
) -> str:
    meeting_id = create(client)
    add_segments(settings, meeting_id, segments)
    set_fields(settings.database_path, meeting_id, status="transcribed")
    return meeting_id


def _url(meeting_id: str, label: str) -> str:
    return f"/api/meetings/{meeting_id}/speakers/{label}/sample"


def test_sample_is_wav_from_longest_segment_capped_at_10s(
    idle: TestClient, settings: Settings, clips: list[tuple[str, float, float]]
) -> None:
    """`participants` 2."""
    meeting_id = _meeting(
        idle,
        settings,
        [("SPEAKER_00", 0.0, 3.0), ("SPEAKER_01", 3.0, 5.0), ("SPEAKER_00", 5.0, 30.0)],
    )

    response = idle.get(_url(meeting_id, "SPEAKER_00"))

    assert response.status_code == 200
    assert response.headers["content-type"] == "audio/wav"
    assert response.headers["cache-control"] == "no-store"
    assert response.content == WAV
    assert clips == [(meeting_id, 5.0, 15.0)]


def test_tie_uses_earliest_longest_segment(
    idle: TestClient, settings: Settings, clips: list[tuple[str, float, float]]
) -> None:
    """`participants` 3."""
    meeting_id = _meeting(
        idle,
        settings,
        [("SPEAKER_00", 1.0, 13.0), ("SPEAKER_01", 13.0, 14.0), ("SPEAKER_00", 20.0, 32.0)],
    )

    idle.get(_url(meeting_id, "SPEAKER_00"))

    assert clips == [(meeting_id, 1.0, 11.0)]


def test_short_longest_segment_gives_its_duration(
    idle: TestClient, settings: Settings, clips: list[tuple[str, float, float]]
) -> None:
    """`participants` 4."""
    meeting_id = _meeting(idle, settings, [("SPEAKER_00", 2.0, 3.0), ("SPEAKER_00", 4.0, 8.5)])

    idle.get(_url(meeting_id, "SPEAKER_00"))

    assert clips == [(meeting_id, 4.0, 8.5)]


def test_unknown_speaker_is_404(
    idle: TestClient, settings: Settings, clips: list[tuple[str, float, float]]
) -> None:
    """`participants` 5."""
    meeting_id = _meeting(idle, settings, [("SPEAKER_00", 0.0, 4.0)])

    response = idle.get(_url(meeting_id, "SPEAKER_09"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "speaker_not_found"
    assert clips == []


@pytest.mark.parametrize("label", ["SPEAKER-00", "a" * 33, "SPEAKER%2000"])
def test_malformed_label_is_422(
    idle: TestClient, settings: Settings, clips: list[tuple[str, float, float]], label: str
) -> None:
    """SEC-09: rótulo validado na borda."""
    meeting_id = _meeting(idle, settings, [("SPEAKER_00", 0.0, 4.0)])

    assert idle.get(_url(meeting_id, label)).status_code == 422
    assert clips == []


def test_missing_treated_audio_is_404_without_path(idle: TestClient, settings: Settings) -> None:
    """Sem `treated.flac`: 404 e nenhum caminho interno no corpo (03-security, "Never")."""
    meeting_id = _meeting(idle, settings, [("SPEAKER_00", 0.0, 4.0)])

    response = idle.get(_url(meeting_id, "SPEAKER_00"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "sample_unavailable"
    assert str(settings.audio_root) not in response.text
    assert "treated" not in response.text


def test_other_users_meeting_is_404(
    idle: TestClient, settings: Settings, users: Users, clips: list[tuple[str, float, float]]
) -> None:
    """`participants` 23; SEC-02."""
    meeting_id = _meeting(idle, settings, [("SPEAKER_00", 0.0, 4.0)])
    users.use("bia")

    response = idle.get(_url(meeting_id, "SPEAKER_00"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "meeting_not_found"
    assert clips == []


def test_without_session_is_401(client: TestClient) -> None:
    """`participants` 24; SEC-01."""
    url = _url("00000000-0000-0000-0000-000000000000", "SPEAKER_00")
    assert client.get(url).status_code == 401
