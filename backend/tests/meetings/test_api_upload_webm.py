"""webm do `MediaRecorder` sem duração no cabeçalho (`meetings` 47 e 48; `screen-recording` 25)."""

import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core import files
from snook.core.events import Event
from snook.core.settings import Settings
from snook.modules.meetings import media_probe
from snook.modules.meetings.media_probe import FfprobeProbe
from tests.meetings.helpers import FIXTURES, meeting_rows, requires_ffprobe, stored_files, upload


@pytest.fixture
def real_probe(app: FastAPI) -> FfprobeProbe:
    probe = FfprobeProbe()
    app.state.media_probe = probe
    return probe


class _HeaderlessWebm:
    """ffprobe fake: trilha de áudio, cabeçalho sem duração e último pacote em `last_pts`."""

    def __init__(self, last_pts: float) -> None:
        self.last_pts = last_pts
        self.commands: list[list[str]] = []

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        assert kwargs["shell"] is False
        self.commands.append(command)
        if "packet=pts_time,duration_time" in command:
            stdout = f"0.000000,0.020000\n{self.last_pts:.6f},0.020000\n".encode()
        else:
            stdout = b'{"streams": [{"codec_type": "audio"}], "format": {}}'
        return subprocess.CompletedProcess(command, 0, stdout=stdout, stderr=b"")


@requires_ffprobe
def test_recorder_webm_gets_real_duration(
    ana: TestClient, real_probe: FfprobeProbe, settings: Settings
) -> None:
    """`meetings` 47: duração lida pelo último pacote, erro máximo de 1 s."""
    content = (FIXTURES / "recorder.webm").read_bytes()
    response = upload(ana, "gravacao.webm", content)
    assert response.status_code == 201
    assert response.json()["duration_seconds"] == pytest.approx(3.0, abs=1.0)
    stored = settings.audio_root / response.json()["id"] / "original.webm"
    assert stored.read_bytes() == content


def test_headerless_webm_above_two_hours_is_refused(
    ana: TestClient,
    real_probe: FfprobeProbe,
    settings: Settings,
    events: list[Event],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`meetings` 48: mesma recusa do critério 11, sem arquivo grande."""
    fake = _HeaderlessWebm(last_pts=7200.99)
    monkeypatch.setattr(media_probe.subprocess, "run", fake)
    response = upload(ana, "gravacao.webm", b"webm falso")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "too_long"
    assert "2 horas" in response.json()["error"]["message"]
    assert len(fake.commands) == 2
    assert meeting_rows(settings.database_path) == []
    assert stored_files(settings.audio_root) == []
    assert events == []


def test_headerless_webm_within_two_hours_is_accepted(
    ana: TestClient, real_probe: FfprobeProbe, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(media_probe.subprocess, "run", _HeaderlessWebm(last_pts=7199.0))
    response = upload(ana, "gravacao.webm", b"webm falso")
    assert response.status_code == 201
    assert response.json()["duration_seconds"] == pytest.approx(7199.02)


def test_duration_command_has_only_server_path(
    ana: TestClient,
    real_probe: FfprobeProbe,
    settings: Settings,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SEC-11: nas duas leituras, sem shell e só o caminho gerado pelo servidor."""
    fake = _HeaderlessWebm(last_pts=10.0)
    monkeypatch.setattr(media_probe.subprocess, "run", fake)
    upload(ana, "-i x; rm -rf.webm", b"webm falso")
    assert len(fake.commands) == 2
    for command in fake.commands:
        assert command[-2] == "-i"
        assert "rm -rf" not in " ".join(command)
        assert Path(command[-1]).parent == files.tmp_dir(settings.audio_root)
