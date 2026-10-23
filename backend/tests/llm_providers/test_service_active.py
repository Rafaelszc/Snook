"""Interface "Provedor ativo": `llm-providers` 22, 26, 31; SEC-26 (Task 16.1)."""

import dataclasses
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session, sessionmaker

from snook.modules.llm_providers import service
from snook.modules.llm_providers.crypto import KeyCipher
from tests.llm_providers.conftest import API_KEY, OTHER_KEY, new_uow

NOW = datetime(2026, 10, 23, 12, 0, tzinfo=UTC)
CIPHER = KeyCipher(bytes(range(32)))


def _save(
    factory: sessionmaker[Session],
    user_id: str,
    provider: str,
    model: str,
    window: int,
    *,
    active: bool,
    api_key: str = API_KEY,
) -> None:
    with new_uow(factory) as uow:
        service.save_config(
            uow,
            CIPHER,
            user_id=user_id,
            provider=provider,
            model=model,
            context_window=window,
            api_key=None if provider == "ollama" else api_key,
            base_url="http://host.docker.internal:11434" if provider == "ollama" else None,
            now=NOW,
        )
    if active:
        with new_uow(factory) as uow:
            service.activate_config(uow, user_id=user_id, provider=provider, now=NOW)


def _active(factory: sessionmaker[Session], user_id: str) -> service.ActiveProvider:
    with new_uow(factory) as uow:
        return service.get_active_provider(uow, user_id=user_id)


def test_without_config_raises_no_active_provider(factory: sessionmaker[Session]) -> None:
    """`llm-providers` 22; transversal 4."""
    with pytest.raises(service.NoActiveProvider) as caught:
        _active(factory, "u1")
    assert caught.value.message == "Nenhum provedor ativo. Configure em Configurações."
    assert "Configurações" in caught.value.message


def test_config_without_active_raises_no_active_provider(factory: sessionmaker[Session]) -> None:
    """Remover o ativo deixa o Usuário sem provedor ativo (`llm-providers` 22, 24)."""
    _save(factory, "u1", "deepseek", "deepseek-chat", 128000, active=False)
    _save(factory, "u1", "ollama", "llama3.1:8b", 8192, active=True)
    with new_uow(factory) as uow:
        service.delete_config(uow, user_id="u1", provider="ollama")
    with pytest.raises(service.NoActiveProvider):
        _active(factory, "u1")


def test_returns_provider_model_and_window(factory: sessionmaker[Session]) -> None:
    """`llm-providers` 31."""
    _save(factory, "u1", "openai", "gpt-5-mini", 400000, active=True)
    _save(factory, "u1", "ollama", "qwen2.5:14b", 32768, active=True)
    assert _active(factory, "u1") == service.ActiveProvider(
        provider="ollama", model="qwen2.5:14b", context_window=32768
    )


def test_returns_only_requested_user(factory: sessionmaker[Session]) -> None:
    """`llm-providers` 26; SEC-26."""
    _save(factory, "u1", "anthropic", "claude-sonnet-4-5", 200000, active=True)
    _save(factory, "u2", "deepseek", "deepseek-reasoner", 64000, active=True, api_key=OTHER_KEY)
    assert _active(factory, "u1").provider == "anthropic"
    assert _active(factory, "u2") == service.ActiveProvider(
        provider="deepseek", model="deepseek-reasoner", context_window=64000
    )


def test_active_provider_carries_no_key(factory: sessionmaker[Session]) -> None:
    """Nenhuma função da interface devolve a chave decifrada."""
    _save(factory, "u1", "openai", "gpt-5-mini", 400000, active=True)
    active = _active(factory, "u1")
    assert {f.name for f in dataclasses.fields(active)} == {"provider", "model", "context_window"}
    assert API_KEY not in repr(active)
