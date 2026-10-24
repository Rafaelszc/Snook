"""Suíte `models_real` (opcional, à mão): modelos reais, sem fakes. Fora do `pytest` padrão
(`addopts` no pyproject) e do CI (08-deployment). Rodar com o extra `cpu` ou `gpu`:

    cd backend && uv sync --extra cpu && uv run pytest -m models_real

`HF_TOKEN` vem do ambiente ou do `.env` da raiz. Cache em `MODELS_REAL_ROOT`
(padrão `~/.cache/snook/models`); a primeira execução baixa os modelos."""

import os
import shutil
from pathlib import Path

import pytest
from dotenv import dotenv_values

from snook.core.settings import Settings, load_settings
from tests.conftest import VALID_MASTER_KEY

FIXTURE = Path(__file__).parents[1] / "fixtures" / "audio" / "two_voices_ptbr.wav"
FIXTURE_SECONDS = 21.6
REPO_ENV = Path(__file__).parents[3] / ".env"
# Lidos na coleta, antes de `clean_env` limpar o ambiente do teste.
_HF_TOKEN = os.environ.get("HF_TOKEN") or dotenv_values(REPO_ENV).get("HF_TOKEN")
_MODELS_ROOT = Path(os.environ.get("MODELS_REAL_ROOT", Path.home() / ".cache/snook/models"))


@pytest.fixture(autouse=True)
def _requires_engines() -> None:
    pytest.importorskip("faster_whisper", reason="extra cpu ou gpu ausente")
    pytest.importorskip("pyannote.audio", reason="extra cpu ou gpu ausente")


@pytest.fixture
def real_settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    if not _HF_TOKEN:
        pytest.skip("HF_TOKEN ausente")
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("HF_TOKEN", _HF_TOKEN)
    monkeypatch.setenv("MODELS_ROOT", str(_MODELS_ROOT))
    monkeypatch.setenv("AUDIO_ROOT", str(tmp_path / "audios"))
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "snook.db"))
    _MODELS_ROOT.mkdir(parents=True, exist_ok=True)
    return load_settings(env_file=None)


@pytest.fixture
def requires_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg ausente")
