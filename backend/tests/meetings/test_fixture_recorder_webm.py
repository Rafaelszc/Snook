"""Fixture `recorder.webm` no formato do `MediaRecorder` (`screen-recording` 25; Q61)."""

import json
import subprocess

from tests.meetings.helpers import FIXTURES, requires_ffprobe

RECORDER = FIXTURES / "recorder.webm"


def _ffprobe(*args: str) -> str:
    completed = subprocess.run(  # noqa: S603
        ["ffprobe", "-v", "error", *args, str(RECORDER)],  # noqa: S607
        capture_output=True,
        check=True,
    )
    return completed.stdout.decode()


@requires_ffprobe
def test_header_has_no_duration() -> None:
    assert _ffprobe("-show_entries", "format=duration", "-of", "csv=p=0").strip() == "N/A"


@requires_ffprobe
def test_single_opus_audio_track_and_no_video() -> None:
    info = json.loads(_ffprobe("-show_entries", "stream=codec_type,codec_name", "-of", "json"))
    assert info["streams"] == [{"codec_type": "audio", "codec_name": "opus"}]
    container = json.loads(_ffprobe("-show_entries", "format=format_name", "-of", "json"))
    assert "webm" in container["format"]["format_name"]


def test_fixture_is_short() -> None:
    """Poucos segundos: cabe no repo (SEC-08)."""
    assert RECORDER.stat().st_size < 64 * 1024
