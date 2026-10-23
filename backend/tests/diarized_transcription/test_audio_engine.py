import json
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.dispatcher import TranscriptionDispatcher
from snook.modules.diarized_transcription.engines import audio
from snook.modules.diarized_transcription.engines.audio import FfmpegAudio, treat_timeout
from snook.modules.diarized_transcription.engines.base import EngineFailure
from snook.modules.diarized_transcription.engines.fakes import FakeEngines, fake_engines
from tests.diarized_transcription.helpers import create, state
from tests.meetings.helpers import FIXTURES, FORMATS

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None, reason="ffmpeg ausente"
)


def _stream(path: Path) -> dict[str, Any]:
    output = subprocess.run(  # noqa: S603
        ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,channels,sample_rate"]  # noqa: S607
        + ["-of", "json", str(path)],
        capture_output=True,
        check=True,
    )
    [stream] = json.loads(output.stdout)["streams"]
    return dict(stream)


@requires_ffmpeg
@pytest.mark.parametrize("ext", FORMATS)
def test_each_format_becomes_mono_16khz_flac(tmp_path: Path, ext: str) -> None:
    """ADR-0014: saída conferida por `ffprobe`."""
    target = tmp_path / "treated.flac"
    FfmpegAudio().treat(FIXTURES / f"tone.{ext}", target, 1.0)
    assert _stream(target) == {"codec_name": "flac", "channels": 1, "sample_rate": "16000"}


@pytest.fixture
def engines() -> FakeEngines:
    """ffmpeg real; diarização e transcrição falsas."""
    fakes = fake_engines()
    return FakeEngines(audio=FfmpegAudio(), diarizer=fakes.diarizer, transcriber=fakes.transcriber)  # type: ignore[arg-type]


@requires_ffmpeg
@pytest.mark.usefixtures("probe", "clock")
@pytest.mark.parametrize("ext", FORMATS)
def test_upload_of_each_format_reaches_transcribed(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher, ext: str
) -> None:
    """`diarized-transcription` 5; transversal 13."""
    content = (FIXTURES / f"tone.{ext}").read_bytes()
    meeting_id = create(ana, name=f"tone.{ext}", content=content)
    assert state(settings.database_path, meeting_id) == ("transcribed", None, None)
    assert _stream(settings.audio_root / meeting_id / "treated.flac")["codec_name"] == "flac"


class _Recorder:
    def __init__(self, returncode: int = 0) -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.returncode = returncode

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, self.returncode, stdout=b"", stderr=b"")


def test_command_has_only_server_paths_no_shell_and_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """SEC-11, SEC-25: caminhos do servidor, `shell=False`, timeout `max(600, 2 * duração)`."""
    recorder = _Recorder()
    monkeypatch.setattr(audio.subprocess, "run", recorder)
    source = tmp_path / "3f2b8c1e" / "original.mp3"
    target = tmp_path / ".tmp" / "9a8b7c6d.flac"
    FfmpegAudio().treat(source, target, 1800.0)
    [(command, kwargs)] = recorder.calls
    assert command[0] == "ffmpeg"
    assert command[command.index("-i") + 1] == str(source)
    assert command[-1] == str(target)
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 3600.0


def test_timeout_has_floor_of_600_seconds() -> None:
    assert treat_timeout(10.0) == 600
    assert treat_timeout(400.0) == 800.0


def test_relative_path_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        FfmpegAudio().treat(Path("original.mp3"), tmp_path / "t.flac", 1.0)


def test_timeout_becomes_treatment_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-25: ffmpeg preso vira falha de tratamento e não deixa saída parcial."""
    target = tmp_path / "t.flac"

    def slow(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        target.write_bytes(b"parcial")
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(audio.subprocess, "run", slow)
    with caplog.at_level(logging.WARNING), pytest.raises(EngineFailure) as caught:
        FfmpegAudio().treat(tmp_path / "a.mp3", target, 1.0)
    assert caught.value.message == messages.AUDIO_FAILED
    assert "audio.treat_timeout" in caplog.text
    assert not target.exists()


def test_nonzero_exit_becomes_treatment_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(audio.subprocess, "run", _Recorder(returncode=1))
    with pytest.raises(EngineFailure) as caught:
        FfmpegAudio().treat(tmp_path / "a.mp3", tmp_path / "t.flac", 1.0)
    assert caught.value.message == messages.AUDIO_FAILED


def test_missing_binary_becomes_treatment_failure(tmp_path: Path) -> None:
    with pytest.raises(EngineFailure) as caught:
        FfmpegAudio(binary=str(tmp_path / "sem-ffmpeg")).treat(
            tmp_path / "a.mp3", tmp_path / "t.flac", 1.0
        )
    assert caught.value.message == messages.AUDIO_FAILED
