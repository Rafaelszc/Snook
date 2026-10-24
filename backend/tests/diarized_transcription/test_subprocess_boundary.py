"""Task 26.3: o subprocesso recebe só caminho e parâmetros, não toca o banco e não manda áudio
para fora do servidor (`03-security.md`, fronteira 3; `diarized-transcription` 21; RT-06)."""

import pickle
import pickletools
from dataclasses import replace
from pathlib import Path

from snook.core.settings import Settings
from snook.modules.diarized_transcription.dispatcher import process_pool
from snook.modules.diarized_transcription.engines.base import Engines
from snook.modules.diarized_transcription.pipeline import Job
from snook.modules.diarized_transcription.service import build_engines
from tests.diarized_transcription import boundary_child as child

FORBIDDEN = ("sqlalchemy", "snook.core", "snook.main", "fastapi", "starlette")


def job(tmp_path: Path) -> Job:
    original = tmp_path / "meeting" / "original.mp3"
    original.parent.mkdir()
    original.write_bytes(b"audio falso")
    return Job(
        original_path=original,
        treated_path=tmp_path / "tmp.flac",
        duration_seconds=10.0,
        expected_speakers=2,
    )


def pickled_strings(payload: object) -> set[str]:
    """Textos do pickle que atravessa o `spawn`: nomes de módulo, classe e valores."""
    return {
        arg for _op, arg, _pos in pickletools.genops(pickle.dumps(payload)) if isinstance(arg, str)
    }


def test_payload_has_only_paths_and_parameters(settings: Settings, tmp_path: Path) -> None:
    """Fronteira 3: engines e trabalho levam só caminho e parâmetros; nada de banco ou app."""
    strings = pickled_strings((build_engines(settings), job(tmp_path)))
    assert "snook.modules.diarized_transcription.engines.whisper" in strings
    assert not [text for text in strings if text.startswith(FORBIDDEN)]


def test_payload_paths_are_server_paths(settings: Settings, tmp_path: Path) -> None:
    payload = job(tmp_path)
    assert payload.original_path.is_absolute() and payload.treated_path.is_absolute()


def test_spawned_job_touches_no_db_and_no_network(settings: Settings, tmp_path: Path) -> None:
    """`diarized-transcription` 21: com a rede bloqueada, o trabalho termina sem tentar conexão
    e o subprocesso não carrega banco nem app."""
    real = build_engines(settings)
    engines = Engines(
        audio=child.CopyAudio(),
        diarizer=replace(real.diarizer, load=child.load_pyannote, decode=child.decode),
        transcriber=replace(real.transcriber, fetch=child.fetch, load=child.load_whisper),
    )
    pool = process_pool(1)
    try:
        result = pool.submit(child.run_guarded, engines, job(tmp_path)).result(timeout=60)
    finally:
        pool.shutdown()
    assert result == {
        "segments": 2,
        "network_attempts": 0,
        "db_modules": [],
        "app_modules": [],
    }
