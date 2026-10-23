import io
import subprocess
import uuid
import wave
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.core.files import UnsafePathError
from snook.core.settings import Settings
from snook.modules.diarized_transcription import service
from snook.modules.diarized_transcription.dispatcher import TranscriptionDispatcher
from snook.modules.diarized_transcription.engines import audio
from snook.modules.diarized_transcription.engines.audio import AudioClipError, FfmpegAudio
from snook.modules.diarized_transcription.engines.fakes import FakeEngines, fake_engines
from tests.diarized_transcription.helpers import create, state
from tests.diarized_transcription.test_audio_engine import requires_ffmpeg
from tests.meetings.helpers import FIXTURES


def _seconds(wav: bytes) -> float:
    with wave.open(io.BytesIO(wav)) as reader:
        assert reader.getnchannels() == 1
        assert reader.getframerate() == 16000
        return reader.getnframes() / reader.getframerate()


@pytest.fixture
def engines() -> FakeEngines:
    """ffmpeg real; diarização e transcrição falsas."""
    fakes = fake_engines()
    return FakeEngines(audio=FfmpegAudio(), diarizer=fakes.diarizer, transcriber=fakes.transcriber)  # type: ignore[arg-type]


@requires_ffmpeg
@pytest.mark.usefixtures("probe", "clock")
def test_clip_after_transcribed_has_interval_duration(
    ana: TestClient, settings: Settings, dispatcher: TranscriptionDispatcher
) -> None:
    """`diarized-transcription` 6."""
    content = (FIXTURES / "tone.wav").read_bytes()
    meeting_id = create(ana, name="tone.wav", content=content)
    assert state(settings.database_path, meeting_id)[0] == "transcribed"
    assert (settings.audio_root / meeting_id / "treated.flac").is_file()

    clip = service.treated_audio_clip(settings.audio_root, meeting_id, 0.2, 0.7)

    assert _seconds(clip) == pytest.approx(0.5, abs=0.02)
    assert list((settings.audio_root / ".tmp").iterdir()) == []


def _meeting_dir(root: Path) -> tuple[str, Path]:
    meeting_id = str(uuid.uuid4())
    directory = root / meeting_id
    directory.mkdir(parents=True)
    (root / ".tmp").mkdir(exist_ok=True)
    return meeting_id, directory


def test_clip_before_transcribed_is_unavailable(tmp_path: Path) -> None:
    meeting_id, _ = _meeting_dir(tmp_path)
    with pytest.raises(AudioClipError):
        service.treated_audio_clip(tmp_path, meeting_id, 0.0, 1.0)


def test_clip_refuses_unsafe_meeting_id(tmp_path: Path) -> None:
    """SEC-15: id fora do formato não vira caminho."""
    with pytest.raises(UnsafePathError):
        service.treated_audio_clip(tmp_path, "../outra", 0.0, 1.0)


@pytest.mark.parametrize(("start", "end"), [(-1.0, 1.0), (2.0, 2.0), (3.0, 1.0)])
def test_invalid_interval_is_refused(tmp_path: Path, start: float, end: float) -> None:
    with pytest.raises(ValueError):
        FfmpegAudio().clip(tmp_path / "t.flac", tmp_path / "c.wav", start, end)


def test_clip_command_has_only_server_paths_no_shell_and_timeout(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """SEC-11, SEC-25; temporário apagado mesmo com falha."""
    meeting_id, directory = _meeting_dir(tmp_path)
    (directory / "treated.flac").write_bytes(b"fLaC")
    calls: list[tuple[list[str], dict[str, Any]]] = []

    def failing(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        calls.append((command, kwargs))
        Path(command[-1]).write_bytes(b"parcial")
        return subprocess.CompletedProcess(command, 1, stdout=b"", stderr=b"")

    monkeypatch.setattr(audio.subprocess, "run", failing)
    with pytest.raises(AudioClipError):
        service.treated_audio_clip(tmp_path, meeting_id, 1.0, 4.0)

    [(command, kwargs)] = calls
    assert command[command.index("-i") + 1] == str(directory / "treated.flac")
    assert Path(command[-1]).parent == tmp_path / ".tmp"
    assert command[command.index("-ss") + 1] == "1.000"
    assert command[command.index("-t") + 1] == "3.000"
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == 600
    assert list((tmp_path / ".tmp").iterdir()) == []


def test_clip_timeout_is_unavailable(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    meeting_id, directory = _meeting_dir(tmp_path)
    (directory / "treated.flac").write_bytes(b"fLaC")

    def slow(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(audio.subprocess, "run", slow)
    with pytest.raises(AudioClipError):
        service.treated_audio_clip(tmp_path, meeting_id, 0.0, 1.0)
