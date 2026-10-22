import base64
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings, load_settings
from snook.main import create_app

VALID_MASTER_KEY = base64.urlsafe_b64encode(bytes(range(32))).decode()

_ENV_PREFIXES = (
    "SNOOK_",
    "ALLOWED_",
    "SESSION_",
    "LOGIN_",
    "LLM_",
    "TRANSCRIPTION_",
    "GENERATION_",
    "WHISPER_",
    "PYANNOTE_",
)
_ENV_NAMES = {
    "HF_TOKEN",
    "BCRYPT_ROUNDS",
    "TRUSTED_PROXY_IPS",
    "UPLOAD_MAX_BYTES",
    "MAX_AUDIO_SECONDS",
    "MODELS_OFFLINE",
    "LOG_LEVEL",
    "DATABASE_PATH",
    "AUDIO_ROOT",
    "MODELS_ROOT",
}


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Remove do ambiente do teste toda variável lida pelo Settings."""
    for name in list(os.environ):
        if name.startswith(_ENV_PREFIXES) or name in _ENV_NAMES:
            monkeypatch.delenv(name)
    yield


@pytest.fixture
def settings(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Settings:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("DATABASE_PATH", str(tmp_path / "data" / "snook.db"))
    monkeypatch.setenv("AUDIO_ROOT", str(tmp_path / "audios"))
    monkeypatch.setenv("MODELS_ROOT", str(tmp_path / "models"))
    (tmp_path / "data").mkdir()
    return load_settings(env_file=None)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client
