import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

from snook.modules.meetings import media_probe
from snook.modules.meetings.media_probe import FfprobeProbe
from tests.meetings.helpers import FIXTURES, FORMATS, requires_ffprobe


@requires_ffprobe
@pytest.mark.parametrize("ext", FORMATS)
def test_fixture_of_each_format_has_audio_and_duration(ext: str) -> None:
    """`meetings` 1, 10."""
    result = FfprobeProbe().probe(FIXTURES / f"tone.{ext}")
    assert result.has_audio
    assert result.duration_seconds == pytest.approx(1.0, abs=0.2)


@requires_ffprobe
@pytest.mark.parametrize("name", ["video_only.mp4", "text_as.mp3"])
def test_file_without_audio_track(name: str) -> None:
    """`meetings` 10: `.mp4` só com vídeo e `.mp3` que é texto."""
    result = FfprobeProbe().probe(FIXTURES / name)
    assert not result.has_audio


@requires_ffprobe
def test_webm_without_header_duration_uses_last_packet() -> None:
    """ADR-0014, Q61: sem `format.duration`, lê o fim do último pacote de áudio."""
    path = FIXTURES / "recorder.webm"
    header = subprocess.run(  # noqa: S603
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],  # noqa: S607
        capture_output=True,
        check=True,
    )
    assert header.stdout.strip() == b"N/A"
    result = FfprobeProbe().probe(path)
    assert result.has_audio
    assert result.duration_seconds == pytest.approx(3.0, abs=1.0)


@requires_ffprobe
def test_concat_script_disguised_as_mp3_is_not_followed(tmp_path: Path) -> None:
    """Demuxer fora da lista não abre: um `.mp3` que é script concat não lê outro arquivo."""
    shutil.copy(FIXTURES / "tone.mp3", tmp_path / "tone.mp3")
    disguised = tmp_path / "upload.mp3"
    disguised.write_text("ffconcat version 1.0\nfile 'tone.mp3'\n")
    assert not FfprobeProbe().probe(disguised).has_audio


class _Recorder:
    def __init__(self, stdout: bytes = b'{"streams": [], "format": {}}') -> None:
        self.calls: list[tuple[list[str], dict[str, Any]]] = []
        self.stdout = stdout

    def __call__(self, command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        self.calls.append((command, kwargs))
        return subprocess.CompletedProcess(command, 0, stdout=self.stdout, stderr=b"")


@pytest.mark.parametrize("name", ['"; rm -rf / ;.mp3', "-i x.mp3"])
def test_command_has_only_server_path_and_no_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, name: str
) -> None:
    """SEC-11: argumento é o caminho gerado; nome enviado nunca entra no comando."""
    recorder = _Recorder()
    monkeypatch.setattr(media_probe.subprocess, "run", recorder)
    server_path = tmp_path / ".tmp" / "3f2b8c1e-5d4a-4b6c-9e7f-0a1b2c3d4e5f"
    FfprobeProbe().probe(server_path)
    [(command, kwargs)] = recorder.calls
    assert command[0] == "ffprobe"
    assert command[-2:] == ["-i", str(server_path)]
    assert kwargs["shell"] is False
    assert kwargs["timeout"] == media_probe.PROBE_TIMEOUT_SECONDS
    assert not any(name in arg for arg in command)


def test_relative_path_is_refused() -> None:
    with pytest.raises(ValueError):
        FfprobeProbe().probe(Path("relativo.mp3"))


def test_timeout_counts_as_no_audio(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-25: ffprobe preso vira recusa, não trava a requisição."""

    def slow(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[bytes]:
        raise subprocess.TimeoutExpired(command, kwargs["timeout"])

    monkeypatch.setattr(media_probe.subprocess, "run", slow)
    with caplog.at_level(logging.WARNING):
        result = FfprobeProbe(timeout=1).probe(tmp_path / "a.mp3")
    assert not result.has_audio
    assert "media.probe_timeout" in caplog.text


def test_missing_binary_counts_as_no_audio(tmp_path: Path) -> None:
    result = FfprobeProbe(binary=str(tmp_path / "sem-ffprobe")).probe(tmp_path / "a.mp3")
    assert not result.has_audio


@pytest.mark.parametrize("stdout", [b"nao e json", b'{"streams": [{"codec_type": "video"}]}'])
def test_unreadable_output_or_no_audio_stream(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, stdout: bytes
) -> None:
    monkeypatch.setattr(media_probe.subprocess, "run", _Recorder(stdout))
    assert not FfprobeProbe().probe(tmp_path / "a.mp3").has_audio
