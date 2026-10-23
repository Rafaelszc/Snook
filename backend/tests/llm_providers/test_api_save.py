"""`PUT /api/llm-configs/{provider}`: `llm-providers` 10 a 18, 27 (Task 15.3)."""

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.modules.llm_providers.adapters.base import CredentialRejected, ModelNotFound
from snook.modules.llm_providers.crypto import KeyCipher, SealedKey, decode_master_key
from tests.auth.helpers import rows
from tests.llm_providers.conftest import (
    API_KEY,
    OTHER_KEY,
    FakeAdapter,
    by_provider,
    config_rows,
    save,
)


def _stored_key(db: Path, settings: Settings, provider: str = "openai") -> str:
    [(user_id, ciphertext, nonce, version)] = [
        row[1:]
        for row in rows(
            db, "SELECT provider, user_id, key_ciphertext, key_nonce, key_version FROM llm_configs"
        )
        if row[0] == provider
    ]
    cipher = KeyCipher(decode_master_key(settings.snook_master_key.get_secret_value()))
    sealed = SealedKey(ciphertext=ciphertext, nonce=nonce, version=version)
    return cipher.decrypt(sealed, user_id=user_id, provider=provider)


def test_failed_connection_is_422_and_nothing_saved(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path
) -> None:
    """`llm-providers` 10: sem configuração anterior."""
    fakes["openai"].error = CredentialRejected("unauthorized")
    response = save(ana)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "credential_rejected"
    assert config_rows(db) == []


def test_failed_connection_keeps_previous_config(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, settings: Settings
) -> None:
    """`llm-providers` 10: configuração anterior intacta, chave inclusive."""
    assert save(ana, model="gpt-4o-mini").status_code == 200
    fakes["openai"].error = ModelNotFound("model_not_found")
    response = save(ana, api_key=OTHER_KEY, model="nao-existe")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "model_not_found"
    assert config_rows(db) == [("ana", "openai", "gpt-4o-mini", 400000, 1)]
    assert _stored_key(db, settings) == API_KEY


def test_valid_save_returns_only_mask_and_encrypts(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, settings: Settings
) -> None:
    """`llm-providers` 11, 12."""
    response = save(ana)
    assert response.status_code == 200
    body = response.json()
    assert (body["state"], body["key_mask"]) == ("active", "sk-...cdef")
    assert API_KEY not in response.text
    [(ciphertext,)] = rows(db, "SELECT key_ciphertext FROM llm_configs")
    assert API_KEY.encode() not in ciphertext
    assert _stored_key(db, settings) == API_KEY


@pytest.mark.parametrize(("provider", "missing"), [("ollama", "base_url"), ("openai", "api_key")])
def test_first_config_without_key_or_url_is_422(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, provider: str, missing: str
) -> None:
    """`llm-providers` 13."""
    response = ana.put(f"/api/llm-configs/{provider}", json={"model": "m"})
    assert response.status_code == 422
    assert missing in response.json()["error"]["fields"]
    assert fakes[provider].calls == []
    assert config_rows(db) == []


@pytest.mark.parametrize("provider", ["anthropic", "deepseek"])
def test_first_config_without_key_is_422_for_every_key_provider(
    ana: TestClient, provider: str
) -> None:
    """`llm-providers` 13."""
    assert ana.put(f"/api/llm-configs/{provider}", json={}).status_code == 422


def test_absent_model_and_window_use_defaults(ana: TestClient, db: Path) -> None:
    """`llm-providers` 14, 15."""
    assert save(ana, "deepseek").status_code == 200
    assert save(ana, "ollama", model="", context_window=None).status_code == 200
    assert config_rows(db) == [
        ("ana", "deepseek", "deepseek-chat", 128000, 1),
        ("ana", "ollama", "llama3.1:8b", 8192, 0),
    ]


@pytest.mark.parametrize("window", [0, -5, 1.5, "8192", True, 10_000_001])
def test_window_not_positive_int_is_422(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, window: object
) -> None:
    """`llm-providers` 15."""
    response = save(ana, context_window=window)
    assert response.status_code == 422
    assert "context_window" in response.json()["error"]["fields"]
    assert config_rows(db) == []


def test_first_config_active_second_does_not_change_active(ana: TestClient) -> None:
    """`llm-providers` 16."""
    assert save(ana, "anthropic").json()["state"] == "active"
    assert save(ana, "openai").json()["state"] == "configured"
    states = {p: item["state"] for p, item in by_provider(ana).items()}
    assert states == {
        "openai": "configured",
        "anthropic": "active",
        "deepseek": "not_configured",
        "ollama": "not_configured",
    }


def test_edit_without_key_keeps_key_and_tests_with_it(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, settings: Settings
) -> None:
    """`llm-providers` 17."""
    assert save(ana).status_code == 200
    response = ana.put("/api/llm-configs/openai", json={"model": "gpt-4.1", "context_window": 9})
    assert response.status_code == 200
    target = fakes["openai"].calls[-1]
    assert (target.api_key, target.model, target.context_window) == (API_KEY, "gpt-4.1", 9)
    assert config_rows(db) == [("ana", "openai", "gpt-4.1", 9, 1)]
    assert _stored_key(db, settings) == API_KEY


def test_edit_with_new_key_replaces_after_test(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path, settings: Settings
) -> None:
    """`llm-providers` 18."""
    assert save(ana).status_code == 200
    response = save(ana, api_key=OTHER_KEY)
    assert response.status_code == 200
    assert fakes["openai"].calls[-1].api_key == OTHER_KEY
    assert response.json()["key_mask"] == "sk-...dcba"
    assert _stored_key(db, settings) == OTHER_KEY


def test_ollama_edit_keeps_saved_url(ana: TestClient, fakes: dict[str, FakeAdapter]) -> None:
    assert save(ana, "ollama", base_url="http://gpu.lan:11434").status_code == 200
    response = ana.put("/api/llm-configs/ollama", json={"model": "qwen2.5:7b"})
    assert response.status_code == 200
    assert response.json()["base_url"] == "http://gpu.lan:11434"
    assert fakes["ollama"].calls[-1].base_url == "http://gpu.lan:11434"


def test_bad_ollama_url_on_save_is_422(ana: TestClient, db: Path) -> None:
    """`llm-providers` 38, 40 no salvar."""
    assert save(ana, "ollama", base_url="file:///etc").status_code == 422
    assert save(ana, "ollama", base_url="http://u:p@host").status_code == 422
    assert config_rows(db) == []


def test_unknown_provider_is_404(ana: TestClient) -> None:
    assert save(ana, "gemini").status_code == 404


def test_save_logged_without_key(
    ana: TestClient, fakes: dict[str, FakeAdapter], caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20, `llm-providers` 27: evento sem chave, também na falha."""
    caplog.set_level(logging.DEBUG)
    assert save(ana).status_code == 200
    fakes["openai"].error = CredentialRejected("unauthorized")
    assert save(ana, api_key=OTHER_KEY).status_code == 422
    [event] = [r for r in caplog.records if r.getMessage() == "llm_config.saved"]
    assert (event.provider, bool(event.user_id)) == ("openai", True)
    dumped = caplog.text + json.dumps([vars(r) for r in caplog.records], default=str)
    assert API_KEY not in dumped
    assert OTHER_KEY not in dumped
