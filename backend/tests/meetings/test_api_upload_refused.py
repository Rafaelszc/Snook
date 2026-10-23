"""Em toda recusa: nenhuma Reunião, nenhum arquivo em `/audios` ou `.tmp`, nenhum aviso."""

from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.events import Event
from snook.core.settings import Settings
from snook.modules.meetings.media_probe import ProbeResult
from tests.meetings.helpers import (
    AUDIO,
    FIXTURES,
    URL,
    FakeProbe,
    meeting_rows,
    requires_ffprobe,
    stored_files,
    upload,
)


def _assert_nothing_left(settings: Settings, events: list[Event]) -> None:
    assert meeting_rows(settings.database_path) == []
    assert stored_files(settings.audio_root) == []
    assert events == []


def _error(response: Any) -> dict[str, Any]:
    error: dict[str, Any] = response.json()["error"]
    return error


def _limit(client: TestClient, max_bytes: int) -> None:
    app: FastAPI = client.app  # type: ignore[assignment]
    app.state.settings = app.state.settings.model_copy(update={"upload_max_bytes": max_bytes})


@pytest.mark.parametrize("name", ["reuniao.flac", "notas.txt", "sem_extensao", "audio.mp3.exe"])
def test_extension_outside_list_is_422_with_formats(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event], name: str
) -> None:
    """`meetings` 9."""
    response = upload(ana, name)
    assert response.status_code == 422
    assert _error(response)["code"] == "unsupported_format"
    for ext in ("mp3", "wav", "m4a", "ogg", "webm", "mp4"):
        assert ext in _error(response)["message"]
    assert probe.paths == []
    _assert_nothing_left(settings, events)


def test_file_without_audio_track_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """`meetings` 10."""
    probe.result = ProbeResult(has_audio=False, duration_seconds=None)
    response = upload(ana, "video.mp4")
    assert response.status_code == 422
    assert _error(response)["code"] == "no_audio"
    assert "arquivo sem áudio" in _error(response)["message"].lower()
    _assert_nothing_left(settings, events)


@requires_ffprobe
@pytest.mark.parametrize(
    ("name", "fixture"), [("texto.mp3", "text_as.mp3"), ("video.mp4", "video_only.mp4")]
)
def test_real_file_without_audio_is_422(
    ana: TestClient, settings: Settings, events: list[Event], name: str, fixture: str
) -> None:
    """`meetings` 10, com ffprobe real: `.mp3` que é texto e `.mp4` só com vídeo."""
    response = upload(ana, name, (FIXTURES / fixture).read_bytes())
    assert response.status_code == 422
    assert _error(response)["code"] == "no_audio"
    _assert_nothing_left(settings, events)


def test_longer_than_two_hours_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """`meetings` 11: 2 h e 1 s."""
    probe.result = ProbeResult(has_audio=True, duration_seconds=7201.0)
    response = upload(ana)
    assert response.status_code == 422
    assert _error(response)["code"] == "too_long"
    assert "2 horas" in _error(response)["message"]
    _assert_nothing_left(settings, events)


def test_one_byte_above_limit_is_413_with_500_mb(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """`meetings` 12: limite reduzido, um byte acima."""
    _limit(ana, 1000)
    response = upload(ana, content=b"a" * 1001)
    assert response.status_code == 413
    assert _error(response)["code"] == "payload_too_large"
    assert "500 MB" in _error(response)["message"]
    assert probe.paths == []
    _assert_nothing_left(settings, events)


def test_declared_content_length_far_above_limit_is_413(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """ADR-0018: `Content-Length` acima do limite corta antes de ler o corpo."""
    _limit(ana, 10)
    response = upload(ana, content=b"a" * (2 * 1024 * 1024))
    assert response.status_code == 413
    _assert_nothing_left(settings, events)


def test_empty_file_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """`meetings` 13."""
    response = upload(ana, content=b"")
    assert response.status_code == 422
    assert _error(response)["code"] == "empty_file"
    assert probe.paths == []
    _assert_nothing_left(settings, events)


@pytest.mark.parametrize("value", ["0", "-1", "21", "2.5", "dois", "1e1"])
def test_invalid_expected_speakers_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event], value: str
) -> None:
    """`meetings` 14, SEC-16."""
    response = upload(ana, expected_speakers=value)
    assert response.status_code == 422
    assert _error(response)["code"] == "invalid_expected_speakers"
    assert "expected_speakers" in _error(response)["fields"]
    _assert_nothing_left(settings, events)


def test_title_over_200_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    response = upload(ana, title="x" * 201)
    assert response.status_code == 422
    assert "title" in _error(response)["fields"]
    _assert_nothing_left(settings, events)


def test_extra_field_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """SEC-09."""
    response = upload(ana, user_id="outro")
    assert response.status_code == 422
    assert _error(response)["fields"] == {"user_id": "Campo não permitido."}
    _assert_nothing_left(settings, events)


def test_duplicate_file_field_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    response = ana.post(URL, files=[("file", ("a.mp3", AUDIO)), ("file", ("b.mp3", AUDIO))])
    assert response.status_code == 422
    _assert_nothing_left(settings, events)


def test_missing_file_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    response = ana.post(URL, files={"title": (None, "Sem arquivo")})
    assert response.status_code == 422
    assert "file" in _error(response)["fields"]
    _assert_nothing_left(settings, events)


def test_not_multipart_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    response = ana.post(URL, json={"title": "x"})
    assert response.status_code == 422
    _assert_nothing_left(settings, events)


def test_truncated_multipart_is_422(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    body = b'--b\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\n\r\n' + AUDIO
    response = ana.post(
        URL, content=body, headers={"Content-Type": "multipart/form-data; boundary=b"}
    )
    assert response.status_code == 422
    assert probe.paths == []
    _assert_nothing_left(settings, events)


def test_probe_crash_still_removes_temp(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """SEC-16: falha inesperada também apaga o temporário."""

    def broken(_path: object) -> ProbeResult:
        raise RuntimeError("ffprobe quebrou")

    probe.probe = broken  # type: ignore[method-assign]
    with pytest.raises(RuntimeError, match="ffprobe quebrou"):
        upload(ana)
    _assert_nothing_left(settings, events)
