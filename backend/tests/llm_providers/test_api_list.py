"""`GET /api/llm-configs`: `llm-providers` 1 a 4, 26, 28 (Task 15.1)."""

from fastapi.testclient import TestClient

from tests.llm_providers.conftest import URL, Users, by_provider, save

DEFAULTS = {
    "openai": ("gpt-5-mini", 400000),
    "anthropic": ("claude-sonnet-4-5", 200000),
    "deepseek": ("deepseek-chat", 128000),
    "ollama": ("llama3.1:8b", 8192),
}


def test_without_configs_lists_four_not_configured_with_defaults(ana: TestClient) -> None:
    """`llm-providers` 1."""
    response = ana.get(URL)
    assert response.status_code == 200
    items = response.json()
    assert [i["provider"] for i in items] == ["openai", "anthropic", "deepseek", "ollama"]
    for item in items:
        assert item["state"] == "not_configured"
        assert (item["default_model"], item["default_context_window"]) == DEFAULTS[item["provider"]]
        assert item["model"] is None
        assert item["key_mask"] is None


def test_configured_shows_model_window_active_and_only_mask(ana: TestClient) -> None:
    """`llm-providers` 2, 3."""
    assert save(ana, model="gpt-4o-mini", context_window=128000).status_code == 200
    assert save(ana, "anthropic").status_code == 200
    items = by_provider(ana)
    assert items["openai"] | {"default_model": None} == {
        "provider": "openai",
        "state": "active",
        "model": "gpt-4o-mini",
        "context_window": 128000,
        "key_mask": "sk-...cdef",
        "base_url": None,
        "key_status": "ok",
        "default_model": None,
        "default_context_window": 400000,
    }
    assert items["anthropic"]["state"] == "configured"
    assert items["deepseek"]["state"] == "not_configured"


def test_short_key_mask_shows_no_char(ana: TestClient) -> None:
    """`llm-providers` 3, Q64: menos de 12 caracteres vira `...`."""
    assert save(ana, api_key="sk-curta-1").status_code == 200
    assert by_provider(ana)["openai"]["key_mask"] == "..."


def test_ollama_url_shown_whole(ana: TestClient) -> None:
    """`llm-providers` 4."""
    url = "http://192.168.0.10:11434/ollama"
    assert save(ana, "ollama", base_url=url + "/").status_code == 200
    item = by_provider(ana)["ollama"]
    assert (item["base_url"], item["key_mask"]) == (url, None)


def test_other_user_config_not_listed(users: Users, client: TestClient) -> None:
    """`llm-providers` 26; SEC-26."""
    users.use("bia")
    assert save(client).status_code == 200
    users.use("ana")
    assert {i["state"] for i in by_provider(client).values()} == {"not_configured"}


def test_without_session_is_401(client: TestClient) -> None:
    """`llm-providers` 28."""
    response = client.get(URL)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_models_lists_from_adapter_with_body_key(ana: TestClient, fakes) -> None:  # type: ignore[no-untyped-def]
    response = ana.post(
        f"{URL}/deepseek/models", json={"api_key": "sk-TesteChave-0123456789abcdef"}
    )
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "models": ["model-a", "model-b"],
        "reason": None,
        "message": None,
    }
    assert fakes["deepseek"].calls[-1].api_key == "sk-TesteChave-0123456789abcdef"


def test_models_without_key_or_saved_config_is_422(ana: TestClient) -> None:
    assert ana.post(f"{URL}/deepseek/models", json={}).status_code == 422


def test_models_requires_login(client: TestClient) -> None:
    assert client.post(f"{URL}/deepseek/models", json={}).status_code == 401
