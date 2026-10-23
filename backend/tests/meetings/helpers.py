import shutil
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from snook.modules.meetings.media_probe import ProbeResult
from tests.auth.helpers import rows

URL = "/api/meetings"
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "audio"
AUDIO = b"ID3 bytes de audio falso"
FORMATS = ("mp3", "wav", "m4a", "ogg", "webm", "mp4")

requires_ffprobe = pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe ausente")


class FakeProbe:
    """Sonda trocável: `result` vale para o próximo upload; `paths` guarda o que foi lido."""

    def __init__(self) -> None:
        self.result = ProbeResult(has_audio=True, duration_seconds=60.0)
        self.paths: list[Path] = []

    def probe(self, path: Path) -> ProbeResult:
        self.paths.append(path)
        return self.result


def upload(
    client: TestClient, name: str = "reuniao.mp3", content: bytes = AUDIO, **data: Any
) -> Any:
    return client.post(URL, files={"file": (name, content, "application/octet-stream")}, data=data)


def meeting_rows(db: Path) -> list[tuple[Any, ...]]:
    return rows(db, "SELECT id, title, original_filename, status FROM meetings")


def stored_files(audio_root: Path) -> list[Path]:
    """Tudo em `/audios`, inclusive `.tmp`, menos o próprio diretório `.tmp`."""
    tmp = audio_root / ".tmp"
    return sorted(path for path in audio_root.rglob("*") if path != tmp)
