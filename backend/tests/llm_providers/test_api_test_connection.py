"""`POST /api/llm-configs/{provider}/test`: `llm-providers` 5 a 9, 27, 38 a 40 (Task 15.2)."""

import logging
import sqlite3
from pathlib import Path

import httpx
import pytest
import respx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.modules.llm_providers.adapters.base import (
    CredentialRejected,
    LLMError,
    ModelNotFound,
    ProviderRateLimited,
    ProviderUnreachable,
)
from snook.modules.llm_providers.adapters.ollama import OllamaAdapter
from tests.auth.helpers import rows
from tests.llm_providers.conftest import API_KEY, OTHER_KEY, URL, FakeAdapter, Users, save


def _test(client: TestClient, provider: str = "openai", **body: object) -> httpx.Response:
    return client.post(f"{URL}/{provider}/test", json=body)


def _config_count(db: Path) -> int:
    return int(rows(db, "SELECT COUNT(*) FROM llm_configs")[0][0])


def test_valid_key_ok_and_nothing_saved(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path
) -> None:
    """`llm-providers` 5."""
    response = _test(ana, api_key=API_KEY, model="gpt-4o-mini", context_window=1000)
    assert response.status_code == 200
    assert response.json() == {"ok": True, "reason": None, "message": None}
    [target] = fakes["openai"].calls
    assert (target.api_key, target.model, target.context_window) == (API_KEY, "gpt-4o-mini", 1000)
    assert _config_count(db) == 0


def test_absent_model_and_window_use_defaults(
    ana: TestClient, fakes: dict[str, FakeAdapter]
) -> None:
    assert _test(ana, "anthropic", api_key=API_KEY, model="  ").json()["ok"] is True
    [target] = fakes["anthropic"].calls
    assert (target.model, target.context_window) == ("claude-sonnet-4-5", 200000)


@pytest.mark.parametrize(
    ("provider", "error", "reason"),
    [
        ("openai", CredentialRejected("unauthorized"), "credential_rejected"),
        ("ollama", ProviderUnreachable("network"), "provider_unreachable"),
        ("deepseek", ModelNotFound("model_not_found"), "model_not_found"),
        ("anthropic", ProviderRateLimited("rate_limited"), "rate_limited"),
    ],
)
def test_failure_returns_reason_and_saves_nothing(
    ana: TestClient,
    fakes: dict[str, FakeAdapter],
    db: Path,
    provider: str,
    error: LLMError,
    reason: str,
) -> None:
    """`llm-providers` 6, 7, 8."""
    fakes[provider].error = error
    body = {"base_url": "http://ollama:11434"} if provider == "ollama" else {"api_key": API_KEY}
    response = _test(ana, provider, **body)
    assert response.status_code == 200
    assert response.json() == {"ok": False, "reason": reason, "message": error.message}
    assert _config_count(db) == 0


def test_key_not_in_response_nor_logs(
    ana: TestClient, fakes: dict[str, FakeAdapter], caplog: pytest.LogCaptureFixture
) -> None:
    """`llm-providers` 9, 27; SEC-07: também quando o provedor recusa."""
    caplog.set_level(logging.DEBUG)
    fakes["openai"].error = CredentialRejected("unauthorized")
    response = _test(ana, api_key=API_KEY)
    assert API_KEY not in response.text
    assert API_KEY not in caplog.text


def test_empty_key_uses_saved_key(ana: TestClient, fakes: dict[str, FakeAdapter]) -> None:
    """05-api: `api_key` vazio com configuração salva usa a chave salva."""
    assert save(ana, model="gpt-4o-mini").status_code == 200
    assert _test(ana, api_key="", context_window=5000).json()["ok"] is True
    target = fakes["openai"].calls[-1]
    assert (target.api_key, target.model, target.context_window) == (API_KEY, "gpt-4o-mini", 5000)


def test_new_key_overrides_saved(ana: TestClient, fakes: dict[str, FakeAdapter]) -> None:
    assert save(ana).status_code == 200
    _test(ana, api_key=OTHER_KEY)
    assert fakes["openai"].calls[-1].api_key == OTHER_KEY


def test_unreadable_saved_key_fails_without_calling_provider(
    ana: TestClient, fakes: dict[str, FakeAdapter], db: Path
) -> None:
    """ADR-0009: chave que não decifra fica `unreadable` e o teste pede a chave de novo."""
    assert save(ana).status_code == 200
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE llm_configs SET key_version = key_version + 1")
    calls = len(fakes["openai"].calls)
    body = _test(ana).json()
    assert (body["ok"], body["reason"]) == (False, "credential_rejected")
    assert "ilegível" in body["message"]
    assert len(fakes["openai"].calls) == calls
    assert rows(db, "SELECT key_status FROM llm_configs") == [("unreadable",)]


def test_key_provider_without_key_and_config_is_422(ana: TestClient) -> None:
    response = _test(ana)
    assert response.status_code == 422
    assert "api_key" in response.json()["error"]["fields"]


@pytest.mark.parametrize(
    ("url", "code"),
    [
        ("file:///etc/passwd", "invalid_url_scheme"),
        ("ftp://host:21", "invalid_url_scheme"),
        ("http://usuario:s3gr3d0@host:11434", "url_with_credentials"),
        ("http://:11434", "invalid_url"),
    ],
)
def test_bad_ollama_url_is_422(
    ana: TestClient, fakes: dict[str, FakeAdapter], url: str, code: str
) -> None:
    """`llm-providers` 38, 40: sem chamada ao provedor e sem a URL na resposta."""
    response = _test(ana, "ollama", base_url=url)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == code
    assert "s3gr3d0" not in response.text
    assert fakes["ollama"].calls == []


@pytest.mark.parametrize(
    "url", ["http://localhost:11434", "http://host.docker.internal:11434", "https://10.0.0.5"]
)
def test_any_http_host_accepted(ana: TestClient, fakes: dict[str, FakeAdapter], url: str) -> None:
    """`llm-providers` 38."""
    assert _test(ana, "ollama", base_url=url).json()["ok"] is True


def test_ollama_rejects_key_and_others_reject_url(ana: TestClient) -> None:
    assert _test(ana, "ollama", base_url="http://h", api_key=API_KEY).status_code == 422
    assert _test(ana, api_key=API_KEY, base_url="http://h").status_code == 422


def test_ollama_without_url_is_422(ana: TestClient) -> None:
    response = _test(ana, "ollama")
    assert response.status_code == 422
    assert "base_url" in response.json()["error"]["fields"]


def test_unknown_provider_is_404(ana: TestClient) -> None:
    response = _test(ana, "gemini", api_key=API_KEY)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "provider_not_found"


def test_extra_field_is_422(ana: TestClient) -> None:
    assert _test(ana, api_key=API_KEY, user_id="outro").status_code == 422


def test_without_session_is_401(client: TestClient) -> None:
    """`llm-providers` 28."""
    assert _test(client, api_key=API_KEY).status_code == 401


def test_real_ollama_adapter_refuses_redirect(
    app: FastAPI, users: Users, client: TestClient, db: Path
) -> None:
    """`llm-providers` 39: adapter real, resposta 302 gravada."""
    app.state.llm_adapters = {"ollama": OllamaAdapter(read_timeout=5)}
    users.use("ana")
    with respx.mock(assert_all_called=True) as mock:
        mock.post("http://ollama.lan:11434/api/show").mock(
            return_value=httpx.Response(302, headers={"location": "http://169.254.169.254/"})
        )
        body = _test(client, "ollama", base_url="http://ollama.lan:11434").json()
        assert (body["ok"], body["reason"]) == (False, "provider_unreachable")
        assert "redirecionamento" in body["message"]
    assert _config_count(db) == 0
