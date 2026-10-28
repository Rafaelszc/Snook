"""Suíte `llm_real` (opcional, à mão): chamada real a cada provedor, sem fakes. Fora do `pytest`
padrão (`addopts` no pyproject) e do CI (08-deployment). Chaves no ambiente ou no `.env` da raiz:

    cd backend && uv run pytest -m llm_real

`SNOOK_TEST_OPENAI_KEY`, `SNOOK_TEST_ANTHROPIC_KEY`, `SNOOK_TEST_DEEPSEEK_KEY`,
`SNOOK_TEST_OLLAMA_URL` (06-integrations). Provedor sem variável é pulado. Modelo padrão de
`defaults.py`, trocável por `SNOOK_TEST_<PROVIDER>_MODEL`; janela sempre a padrão."""

import os
from pathlib import Path

import pytest
from dotenv import dotenv_values

from snook.core.logging import register_secret
from snook.modules.llm_providers.adapters.base import ProviderTarget
from snook.modules.llm_providers.defaults import DEFAULTS

REPO_ENV = Path(__file__).parents[3] / ".env"
_ENV_NAMES = {
    "openai": "SNOOK_TEST_OPENAI_KEY",
    "anthropic": "SNOOK_TEST_ANTHROPIC_KEY",
    "deepseek": "SNOOK_TEST_DEEPSEEK_KEY",
    "ollama": "SNOOK_TEST_OLLAMA_URL",
}
# Lidos na coleta, antes de `clean_env` limpar o ambiente do teste.
_DOTENV = dotenv_values(REPO_ENV)
_VALUES = {
    provider: os.environ.get(name) or _DOTENV.get(name) for provider, name in _ENV_NAMES.items()
}
_MODELS = {
    provider: os.environ.get(f"SNOOK_TEST_{provider.upper()}_MODEL")
    or _DOTENV.get(f"SNOOK_TEST_{provider.upper()}_MODEL")
    for provider in _ENV_NAMES
}

PROVIDERS = list(_ENV_NAMES)


@pytest.fixture(params=PROVIDERS)
def target(request: pytest.FixtureRequest) -> tuple[str, ProviderTarget]:
    provider: str = request.param
    value = _VALUES[provider]
    if not value:
        pytest.skip(f"{_ENV_NAMES[provider]} ausente")
    defaults = DEFAULTS[provider]
    model = _MODELS[provider] or defaults.model
    if provider == "ollama":
        return provider, ProviderTarget(
            model=model, base_url=value, context_window=defaults.context_window
        )
    register_secret(value)
    return provider, ProviderTarget(
        model=model, api_key=value, context_window=defaults.context_window
    )
