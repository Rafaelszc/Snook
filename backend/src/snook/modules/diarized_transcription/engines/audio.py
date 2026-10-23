"""Tratamento por ffmpeg: mono 16 kHz, passa-alta 80 Hz, `loudnorm`, FLAC (ADR-0014).
Só caminhos gerados pelo servidor, sem shell, com timeout (SEC-11, SEC-25)."""

import logging
import subprocess  # noqa: S404 - sem shell, argumentos fixos
from pathlib import Path
from typing import NoReturn

from snook.modules.diarized_transcription import messages
from snook.modules.diarized_transcription.engines.base import EngineFailure

logger = logging.getLogger("snook.transcription.audio")

MIN_TIMEOUT_SECONDS = 600  # `max(600, 2 * duração)` (06-integrations)
SAMPLE_RATE = 16000
FILTERS = f"highpass=f=80,loudnorm,aresample={SAMPLE_RATE}"
# Mesma lista da sonda do upload: playlist ou concat disfarçado não abre outro arquivo.
_FORMAT_WHITELIST = "mp3,wav,mov,mp4,m4a,ogg,matroska,webm"


class AudioClipError(Exception):
    """Corte do áudio tratado falhou. Quem chama devolve erro genérico (06-integrations)."""


def treat_timeout(duration_seconds: float) -> float:
    return max(MIN_TIMEOUT_SECONDS, 2 * duration_seconds)


class FfmpegAudio:
    def __init__(self, binary: str = "ffmpeg") -> None:
        self._binary = binary

    def command(self, source: Path, target: Path) -> list[str]:
        return [
            self._binary,
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-protocol_whitelist",
            "file",
            "-format_whitelist",
            _FORMAT_WHITELIST,
            "-i",
            str(source),
            "-vn",
            "-ac",
            "1",
            "-af",
            FILTERS,
            "-ar",
            str(SAMPLE_RATE),
            "-c:a",
            "flac",
            str(target),
        ]

    def treat(self, source: Path, target: Path, duration_seconds: float) -> None:
        if not source.is_absolute() or not target.is_absolute():
            raise ValueError("caminho do servidor deve ser absoluto")
        timeout = treat_timeout(duration_seconds)
        try:
            completed = subprocess.run(  # noqa: S603 - lista fixa, shell=False
                self.command(source, target),
                shell=False,
                capture_output=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            logger.warning("audio.treat_timeout", extra={"timeout_seconds": timeout})
            self._fail(target)
        except OSError:
            logger.exception("audio.treat_failed")
            self._fail(target)
        if completed.returncode != 0:
            # stderr do ffmpeg pode citar caminho: fica fora do log (SEC-20).
            logger.warning("audio.treat_failed", extra={"returncode": completed.returncode})
            self._fail(target)

    @staticmethod
    def _fail(target: Path) -> NoReturn:
        target.unlink(missing_ok=True)
        raise EngineFailure(messages.AUDIO_FAILED)

    def clip(self, source: Path, target: Path, start: float, end: float) -> None:
        """Trecho `[start, end)` de `source` em WAV mono 16 kHz, para a amostra (ADR-0014)."""
        if not source.is_absolute() or not target.is_absolute():
            raise ValueError("caminho do servidor deve ser absoluto")
        if not 0 <= start < end:
            raise ValueError("intervalo inválido")
        command = [
            self._binary,
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-protocol_whitelist",
            "file",
            "-ss",
            f"{start:.3f}",
            "-t",
            f"{end - start:.3f}",
            "-i",
            str(source),
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(target),
        ]
        try:
            completed = subprocess.run(  # noqa: S603 - lista fixa, shell=False
                command,
                shell=False,
                capture_output=True,
                timeout=treat_timeout(end - start),
                check=False,
            )
        except (subprocess.TimeoutExpired, OSError) as exc:
            logger.warning("audio.clip_failed", extra={"error": type(exc).__name__})
            target.unlink(missing_ok=True)
            raise AudioClipError from exc
        if completed.returncode != 0:
            logger.warning("audio.clip_failed", extra={"returncode": completed.returncode})
            target.unlink(missing_ok=True)
            raise AudioClipError
