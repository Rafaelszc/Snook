import base64
import os
from collections.abc import Iterator

import pytest

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
