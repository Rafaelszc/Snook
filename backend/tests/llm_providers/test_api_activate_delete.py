"""Ativar e remover: `llm-providers` 19 a 21, 23 a 26, 28 (Task 15.4)."""

import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.auth.helpers import rows
from tests.llm_providers.conftest import API_KEY, URL, Users, by_provider, config_rows, save


def _activate(client: TestClient, provider: str) -> int:
    return client.post(f"{URL}/{provider}/activate").status_code


def _states(client: TestClient) -> dict[str, str]:
    return {p: item["state"] for p, item in by_provider(client).items()}


def test_activate_switches_active(ana: TestClient, db: Path) -> None:
    """`llm-providers` 19, 20."""
    save(ana, "openai")
    save(ana, "ollama")
    response = ana.post(f"{URL}/ollama/activate")
    assert response.status_code == 200
    assert response.json()["state"] == "active"
    assert _states(ana)["openai"] == "configured"
    assert rows(db, "SELECT COUNT(*) FROM llm_configs WHERE is_active = 1") == [(1,)]


def test_activate_already_active_is_idempotent(ana: TestClient) -> None:
    save(ana)
    assert _activate(ana, "openai") == 200
    assert _states(ana)["openai"] == "active"


def test_activate_not_configured_is_409_and_active_unchanged(ana: TestClient) -> None:
    """`llm-providers` 21."""
    save(ana)
    response = ana.post(f"{URL}/anthropic/activate")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "provider_not_configured"
    assert _states(ana)["openai"] == "active"


def test_delete_removes_row_and_encrypted_key(ana: TestClient, db: Path) -> None:
    """`llm-providers` 23."""
    save(ana)
    response = ana.delete(f"{URL}/openai")
    assert response.status_code == 204
    assert rows(db, "SELECT COUNT(*) FROM llm_configs") == [(0,)]
    assert _states(ana)["openai"] == "not_configured"


def test_delete_active_leaves_none_active(ana: TestClient, db: Path) -> None:
    """`llm-providers` 24."""
    save(ana, "openai")
    save(ana, "deepseek")
    assert ana.delete(f"{URL}/openai").status_code == 204
    assert config_rows(db) == [("ana", "deepseek", "deepseek-chat", 128000, 0)]


def test_delete_not_configured_is_404(ana: TestClient) -> None:
    """`llm-providers` 25."""
    response = ana.delete(f"{URL}/openai")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "config_not_found"


@pytest.mark.parametrize("method", ["post", "delete"])
def test_unknown_provider_is_404(ana: TestClient, method: str) -> None:
    path = f"{URL}/gemini/activate" if method == "post" else f"{URL}/gemini"
    response = ana.request(method.upper(), path)
    assert response.json()["error"]["code"] == "provider_not_found"


def test_other_user_config_not_activated_nor_deleted(
    users: Users, client: TestClient, db: Path
) -> None:
    """`llm-providers` 26; SEC-26: Ana não vê, não ativa e não remove a config da Bia."""
    users.use("bia")
    save(client, "openai")
    save(client, "anthropic")
    users.use("ana")
    assert _activate(client, "anthropic") == 409
    assert client.delete(f"{URL}/openai").status_code == 404
    assert config_rows(db) == [
        ("bia", "openai", "gpt-5-mini", 400000, 1),
        ("bia", "anthropic", "claude-sonnet-4-5", 200000, 0),
    ]


def test_users_have_independent_active(users: Users, client: TestClient, db: Path) -> None:
    """Primeira config da Ana fica ativa mesmo com a Bia já tendo uma ativa."""
    users.use("bia")
    save(client, "openai")
    users.use("ana")
    assert save(client, "openai").json()["state"] == "active"
    assert rows(db, "SELECT COUNT(*) FROM llm_configs WHERE is_active = 1") == [(2,)]


@pytest.mark.parametrize(
    ("method", "path"),
    [("POST", f"{URL}/openai/activate"), ("DELETE", f"{URL}/openai"), ("PUT", f"{URL}/openai")],
)
def test_without_session_is_401(client: TestClient, method: str, path: str) -> None:
    """`llm-providers` 28."""
    assert client.request(method, path).status_code == 401


def test_activate_and_delete_logged_without_key(
    ana: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20."""
    caplog.set_level(logging.DEBUG)
    save(ana)
    _activate(ana, "openai")
    ana.delete(f"{URL}/openai")
    names = [r.getMessage() for r in caplog.records]
    assert {"llm_config.activated", "llm_config.deleted"} <= set(names)
    dumped = caplog.text + json.dumps([vars(r) for r in caplog.records], default=str)
    assert API_KEY not in dumped
