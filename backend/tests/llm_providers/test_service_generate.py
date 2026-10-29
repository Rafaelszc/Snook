"""Interface "Gerar": `llm-providers` 27, 29 a 31; SEC-07, SEC-17, SEC-26 (Task 16.3)."""

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

import pytest
import respx
from sqlalchemy.orm import Session, sessionmaker

from snook.core.settings import Settings
from snook.modules.llm_providers import service
from snook.modules.llm_providers.adapters.base import LLMAdapter
from snook.modules.llm_providers.crypto import KeyCipher
from tests.adapters.llm.conftest import recorded
from tests.auth.helpers import rows
from tests.llm_providers.conftest import API_KEY, OTHER_KEY, new_uow

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
CIPHER = KeyCipher(bytes(range(32)))
OLLAMA = "http://host.docker.internal:11434"
URLS = {
    "openai": "https://api.openai.com/v1/chat/completions",
    "anthropic": "https://api.anthropic.com/v1/messages",
    "deepseek": "https://api.deepseek.com/chat/completions",
    "ollama": f"{OLLAMA}/api/chat",
}
MODELS = {
    "openai": "gpt-5-mini",
    "anthropic": "claude-sonnet-4-5",
    "deepseek": "deepseek-chat",
    "ollama": "llama3.1:8b",
}
SCHEMA = {"type": "object", "properties": {"epics": {"type": "array"}}}
EXPECTED = {"epics": [{"title": "Login", "user_stories": []}]}


@pytest.fixture
def adapters(settings: Settings) -> dict[str, LLMAdapter]:
    return service.build_adapters(settings)


def _save(
    factory: sessionmaker[Session],
    provider: str,
    *,
    user_id: str = "u1",
    model: str | None = None,
    api_key: str = API_KEY,
    cipher: KeyCipher = CIPHER,
) -> None:
    with new_uow(factory) as uow:
        service.save_config(
            uow,
            cipher,
            user_id=user_id,
            provider=provider,
            model=model or MODELS[provider],
            context_window=8192,
            api_key=None if provider == "ollama" else api_key,
            base_url=OLLAMA if provider == "ollama" else None,
            now=NOW,
        )
    with new_uow(factory) as uow:
        service.activate_config(uow, user_id=user_id, provider=provider, now=NOW)


def _snapshot(factory: sessionmaker[Session], user_id: str = "u1") -> service.ActiveProvider:
    with new_uow(factory) as uow:
        return service.get_active_provider(uow, user_id=user_id)


def _generate(
    factory: sessionmaker[Session],
    adapters: dict[str, LLMAdapter],
    snapshot: service.ActiveProvider,
    *,
    user_id: str = "u1",
    cipher: KeyCipher = CIPHER,
) -> str:
    return service.generate(
        new_uow(factory),
        cipher,
        adapters,
        user_id=user_id,
        provider_snapshot=snapshot,
        system_prompt="Gere o backlog.",
        content="Ana: precisamos de login.",
        json_schema=SCHEMA,
        max_output_tokens=2048,
    )


@respx.mock
@pytest.mark.parametrize("provider", list(URLS))
def test_generate_returns_recorded_text(
    provider: str, factory: sessionmaker[Session], adapters: dict[str, LLMAdapter]
) -> None:
    """`llm-providers` 29."""
    respx.post(URLS[provider]).mock(return_value=recorded(provider, "generate_success"))
    _save(factory, provider)
    text = _generate(factory, adapters, _snapshot(factory))
    assert json.loads(text) == EXPECTED


@respx.mock
def test_generate_uses_saved_model_and_key(
    factory: sessionmaker[Session], adapters: dict[str, LLMAdapter]
) -> None:
    """`llm-providers` 31."""
    route = respx.post(URLS["openai"]).mock(return_value=recorded("openai", "generate_success"))
    _save(factory, "openai", model="gpt-5-custom")
    _generate(factory, adapters, _snapshot(factory))
    request = route.calls.last.request
    assert json.loads(request.content)["model"] == "gpt-5-custom"
    assert request.headers["authorization"] == f"Bearer {API_KEY}"


@respx.mock
def test_generate_uses_owner_config_only(
    factory: sessionmaker[Session], adapters: dict[str, LLMAdapter]
) -> None:
    """`llm-providers` 26; SEC-26: a chave e o modelo são do `user_id` pedido."""
    route = respx.post(URLS["openai"]).mock(return_value=recorded("openai", "generate_success"))
    _save(factory, "openai", user_id="u1", model="gpt-u1")
    _save(factory, "openai", user_id="u2", model="gpt-u2", api_key=OTHER_KEY)
    _generate(factory, adapters, _snapshot(factory, "u2"), user_id="u2")
    request = route.calls.last.request
    assert json.loads(request.content)["model"] == "gpt-u2"
    assert request.headers["authorization"] == f"Bearer {OTHER_KEY}"


@respx.mock
def test_generate_without_config_of_snapshot_raises_no_active_provider(
    factory: sessionmaker[Session], adapters: dict[str, LLMAdapter]
) -> None:
    """Configuração removida durante a geração: nenhuma chamada ao provedor."""
    route = respx.post(URLS["openai"]).mock(return_value=recorded("openai", "generate_success"))
    _save(factory, "openai")
    snapshot = _snapshot(factory)
    with new_uow(factory) as uow:
        service.delete_config(uow, user_id="u1", provider="openai")
    with pytest.raises(service.NoActiveProvider):
        _generate(factory, adapters, snapshot)
    # Snapshot de outro Usuário não abre a configuração de `u1`.
    _save(factory, "openai")
    with pytest.raises(service.NoActiveProvider):
        _generate(factory, adapters, _snapshot(factory), user_id="u2")
    assert not route.called


@respx.mock
@pytest.mark.parametrize(
    ("provider", "case", "error"),
    [
        ("openai", "unauthorized", service.CredentialRejected),
        ("anthropic", "model_not_found", service.ModelNotFound),
        ("deepseek", "context_exceeded", service.ContextLimitExceeded),
        ("ollama", "server_error", service.ProviderUnreachable),
        ("anthropic", "rate_limited", service.ProviderRateLimited),
    ],
)
def test_typed_errors_rise_without_key(
    provider: str,
    case: str,
    error: type[service.LLMError],
    factory: sessionmaker[Session],
    adapters: dict[str, LLMAdapter],
    caplog: pytest.LogCaptureFixture,
) -> None:
    """`llm-providers` 30, 27; SEC-17."""
    caplog.set_level(logging.DEBUG)
    respx.post(URLS[provider]).mock(return_value=recorded(provider, case))
    _save(factory, provider)
    with pytest.raises(error) as caught:
        _generate(factory, adapters, _snapshot(factory))
    exc = caught.value
    for text in (str(exc), repr(exc), exc.message, exc.reason, caplog.text):
        assert API_KEY not in text


@respx.mock
def test_unreadable_key_raises_credential_rejected_and_marks_config(
    factory: sessionmaker[Session], adapters: dict[str, LLMAdapter], tmp_path: Path
) -> None:
    """ADR-0009: chave ilegível vira "credencial recusada" e fica `unreadable`."""
    route = respx.post(URLS["openai"]).mock(return_value=recorded("openai", "generate_success"))
    _save(factory, "openai")
    other = KeyCipher(bytes(range(32, 64)))
    with pytest.raises(service.CredentialRejected) as caught:
        _generate(factory, adapters, _snapshot(factory), cipher=other)
    assert caught.value.message == "Chave ilegível. Informe a chave de novo em Configurações."
    assert not route.called
    assert rows(tmp_path / "service.db", "SELECT key_status FROM llm_configs") == [("unreadable",)]
