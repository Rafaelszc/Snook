import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core import files
from snook.core.events import Event, MeetingCreated
from snook.core.settings import Settings
from snook.modules.meetings.media_probe import ProbeResult
from tests.auth.helpers import rows
from tests.meetings.helpers import (
    AUDIO,
    FIXTURES,
    FORMATS,
    URL,
    FakeProbe,
    meeting_rows,
    requires_ffprobe,
    stored_files,
    upload,
)


def _stored(settings: Settings, meeting_id: str, ext: str) -> Path:
    return settings.audio_root / meeting_id / f"original.{ext}"


@pytest.mark.parametrize("ext", FORMATS)
def test_each_format_is_created_pending(
    ana: TestClient, probe: FakeProbe, settings: Settings, ext: str
) -> None:
    """`meetings` 1 e 2."""
    response = upload(ana, f"reuniao.{ext}", AUDIO)
    assert response.status_code == 201
    body = response.json()
    assert set(body) >= {"id", "title", "original_filename", "duration_seconds", "created_at"}
    assert body["status"] == "pending"
    assert body["original_filename"] == f"reuniao.{ext}"
    assert body["duration_seconds"] == 60.0
    assert body["created_at"] == "2026-10-23T12:00:00Z"
    assert _stored(settings, body["id"], ext).read_bytes() == AUDIO
    assert rows(settings.database_path, "SELECT id, file_ext FROM meetings") == [(body["id"], ext)]


@requires_ffprobe
@pytest.mark.parametrize("ext", FORMATS)
def test_each_fixture_is_accepted_with_real_ffprobe(
    ana: TestClient, settings: Settings, ext: str
) -> None:
    """`meetings` 1: leitura real de duração com fixture curta."""
    content = (FIXTURES / f"tone.{ext}").read_bytes()
    response = upload(ana, f"reuniao.{ext}", content)
    assert response.status_code == 201
    assert response.json()["duration_seconds"] == pytest.approx(1.0, abs=0.2)
    assert _stored(settings, response.json()["id"], ext).read_bytes() == content


def test_title_is_stripped(ana: TestClient, probe: FakeProbe) -> None:
    """`meetings` 3."""
    response = upload(ana, title="  Planejamento da sprint  ")
    assert response.json()["title"] == "Planejamento da sprint"


@pytest.mark.parametrize("data", [{}, {"title": ""}, {"title": "   "}])
def test_missing_or_blank_title_uses_original_filename(
    ana: TestClient, probe: FakeProbe, data: dict[str, str]
) -> None:
    """`meetings` 4."""
    response = upload(ana, "Daily 23-10.mp3", **data)
    assert response.json()["title"] == "Daily 23-10.mp3"


@pytest.mark.parametrize(("raw", "stored"), [("1", 1), ("20", 20), (" 7 ", 7)])
def test_expected_speakers_is_stored(
    ana: TestClient, probe: FakeProbe, settings: Settings, raw: str, stored: int
) -> None:
    """`meetings` 5."""
    response = upload(ana, expected_speakers=raw)
    assert response.json()["expected_speakers"] == stored
    assert rows(settings.database_path, "SELECT expected_speakers FROM meetings") == [(stored,)]


def test_expected_speakers_absent_is_empty(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 5."""
    response = upload(ana)
    assert response.json()["expected_speakers"] is None
    assert rows(settings.database_path, "SELECT expected_speakers FROM meetings") == [(None,)]


def test_meeting_created_is_published_once_with_id(
    ana: TestClient, probe: FakeProbe, settings: Settings, events: list[Event]
) -> None:
    """`meetings` 6: um aviso, com `id` e `run_id` gravados; arquivo já no lugar."""
    seen_file: list[bool] = []
    app: FastAPI = ana.app  # type: ignore[assignment]
    app.state.event_bus.subscribe(
        MeetingCreated,
        lambda e: seen_file.append(_stored(settings, e.meeting_id, "mp3").exists()),
    )
    meeting_id = upload(ana).json()["id"]
    [(run_id,)] = rows(settings.database_path, "SELECT run_id FROM meetings")
    assert events == [MeetingCreated(meeting_id=meeting_id, run_id=run_id)]
    assert seen_file == [True]


def test_response_does_not_wait_for_processing(ana: TestClient, probe: FakeProbe) -> None:
    """`meetings` 7: consumidor fake inicia trabalho que nunca termina."""
    release = threading.Event()
    started: list[str] = []
    executor = ThreadPoolExecutor(max_workers=1)
    app: FastAPI = ana.app  # type: ignore[assignment]

    def never_ending(event: MeetingCreated) -> None:
        started.append(event.meeting_id)
        executor.submit(release.wait)

    app.state.event_bus.subscribe(MeetingCreated, never_ending)
    try:
        response = upload(ana)
        assert response.status_code == 201
        assert started == [response.json()["id"]]
    finally:
        release.set()
        executor.shutdown()


@pytest.mark.parametrize("name", ["REUNIAO.MP3", "Reuniao.Mp4", "x.WEBM"])
def test_uppercase_extension_counts_as_lowercase(
    ana: TestClient, probe: FakeProbe, settings: Settings, name: str
) -> None:
    """`meetings` 15."""
    response = upload(ana, name)
    assert response.status_code == 201
    ext = name.rsplit(".", 1)[1].lower()
    assert _stored(settings, response.json()["id"], ext).exists()
    assert response.json()["original_filename"] == name


def test_exactly_two_hours_is_accepted(ana: TestClient, probe: FakeProbe) -> None:
    """`meetings` 8."""
    probe.result = ProbeResult(has_audio=True, duration_seconds=7200.0)
    response = upload(ana)
    assert response.status_code == 201
    assert response.json()["duration_seconds"] == 7200.0


def test_exactly_size_limit_is_accepted(ana: TestClient, probe: FakeProbe) -> None:
    """`meetings` 12, ADR-0018: no valor exato do limite, não recusa."""
    app: FastAPI = ana.app  # type: ignore[assignment]
    app.state.settings = app.state.settings.model_copy(update={"upload_max_bytes": 1000})
    assert upload(ana, content=b"a" * 1000).status_code == 201


@pytest.mark.parametrize("name", ['"; rm -rf / ;.mp3', "-i x.mp3"])
def test_probe_gets_only_server_path(
    ana: TestClient, probe: FakeProbe, settings: Settings, name: str
) -> None:
    """SEC-11: nome enviado nunca chega ao ffprobe nem ao disco."""
    response = upload(ana, name)
    assert response.status_code == 201
    [path] = probe.paths
    assert path.parent == files.tmp_dir(settings.audio_root)
    assert files.is_meeting_id(path.name)
    assert name not in str(path)
    stored = [p.name for p in stored_files(settings.audio_root) if p.is_file()]
    assert stored == ["original.mp3"]


@pytest.mark.parametrize(
    ("name", "kept"),
    [("../../etc/passwd.mp3", "passwd.mp3"), ("C:\\Users\\ana\\daily.mp3", "daily.mp3")],
)
def test_original_filename_drops_path(
    ana: TestClient, probe: FakeProbe, name: str, kept: str
) -> None:
    """SEC-16: nome original só como metadado, sem caminho."""
    assert upload(ana, name).json()["original_filename"] == kept


def test_original_filename_is_cut_at_255(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    name = "a" * 300 + ".mp3"
    response = upload(ana, name)
    assert response.status_code == 201
    [(_, title, original, _)] = meeting_rows(settings.database_path)
    assert len(original) == 255
    assert len(title) == 200


def test_response_has_no_internal_path(
    ana: TestClient, probe: FakeProbe, settings: Settings
) -> None:
    """`meetings` 21."""
    response = upload(ana)
    assert str(settings.audio_root) not in response.text
    assert "original.mp3" not in response.text
    assert "file_ext" not in response.json()


def test_upload_without_session_is_401(client: TestClient, probe: FakeProbe) -> None:
    """`meetings` 33, SEC-01."""
    assert upload(client).status_code == 401


def test_upload_without_origin_is_403(ana: TestClient, probe: FakeProbe) -> None:
    """SEC-04."""
    response = ana.post(
        URL, files={"file": ("a.mp3", AUDIO)}, headers={"Origin": "http://evil.example"}
    )
    assert response.status_code == 403
