"""Duração e trilhas por `ffprobe` (ADR-0014). Só caminho gerado pelo servidor (SEC-11)."""

import json
import logging
import subprocess  # noqa: S404 - sem shell, argumentos fixos
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger("snook.meetings.probe")

PROBE_TIMEOUT_SECONDS = 120
# Demuxers dos formatos aceitos. Playlist ou concat disfarçado de .mp3 não abre outro arquivo.
_FORMAT_WHITELIST = "mp3,wav,mov,mp4,m4a,ogg,matroska,webm"


@dataclass(frozen=True)
class ProbeResult:
    has_audio: bool
    duration_seconds: float | None


class MediaProbe(Protocol):
    def probe(self, path: Path) -> ProbeResult: ...


def _positive(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


class FfprobeProbe:
    def __init__(self, binary: str = "ffprobe", timeout: float = PROBE_TIMEOUT_SECONDS) -> None:
        self._binary = binary
        self._timeout = timeout

    def _run(self, path: Path, args: list[str]) -> str | None:
        command = [
            self._binary,
            "-v",
            "error",
            "-protocol_whitelist",
            "file",
            "-format_whitelist",
            _FORMAT_WHITELIST,
            *args,
            "-i",
            str(path),
        ]
        try:
            completed = subprocess.run(  # noqa: S603 - lista fixa, shell=False
                command, shell=False, capture_output=True, timeout=self._timeout, check=False
            )
        except subprocess.TimeoutExpired:
            logger.warning("media.probe_timeout")
            return None
        except OSError:
            logger.exception("media.probe_failed")
            return None
        if completed.returncode != 0:
            return None
        return completed.stdout.decode("utf-8", errors="replace")

    def _last_packet_end(self, path: Path) -> float | None:
        """webm do `MediaRecorder` não traz duração: fim do último pacote de áudio."""
        output = self._run(
            path,
            ["-select_streams", "a:0", "-show_entries", "packet=pts_time,duration_time"]
            + ["-of", "csv=p=0"],
        )
        lines = [line for line in (output or "").splitlines() if line.strip()]
        if not lines:
            return None
        pts, _, duration = lines[-1].partition(",")
        end = (_positive(pts) or 0.0) + (_positive(duration) or 0.0)
        return end or None

    def probe(self, path: Path) -> ProbeResult:
        if not path.is_absolute():
            raise ValueError("caminho do servidor deve ser absoluto")
        output = self._run(
            path, ["-show_entries", "format=duration:stream=codec_type", "-of", "json"]
        )
        if output is None:
            return ProbeResult(has_audio=False, duration_seconds=None)
        try:
            info = json.loads(output)
        except json.JSONDecodeError:
            return ProbeResult(has_audio=False, duration_seconds=None)
        streams = info.get("streams") or []
        if not any(stream.get("codec_type") == "audio" for stream in streams):
            return ProbeResult(has_audio=False, duration_seconds=None)
        duration = _positive((info.get("format") or {}).get("duration"))
        if duration is None:
            duration = self._last_packet_end(path)
        return ProbeResult(has_audio=True, duration_seconds=duration)
