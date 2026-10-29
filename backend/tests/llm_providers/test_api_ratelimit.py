"""Limite de "Testar conexão" e salvar: `llm-providers` 41; SEC-06 (Task 15.5)."""

import json
import logging
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings, load_settings
from snook.main import create_app
from tests.llm_providers.conftest import API_KEY, URL, FakeAdapter, Users, save


def _test(client: TestClient) -> int:
    return client.post(f"{URL}/openai/test", json={"api_key": API_KEY}).status_code


def test_over_limit_is_429_without_provider_call(
    ana: TestClient, fakes: dict[str, FakeAdapter], clock: FakeClock
) -> None:
    """Padrão do ADR-0010: 10 por Usuário em 10 min, teste e salvar somados."""
    for _ in range(5):
        assert _test(ana) == 200
    for _ in range(5):
        assert save(ana).status_code == 200
    calls = len(fakes["openai"].calls)
    response = ana.post(f"{URL}/openai/test", json={"api_key": API_KEY})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert 1 <= int(response.headers["Retry-After"]) <= 600
    assert save(ana).status_code == 429
    assert len(fakes["openai"].calls) == calls

    clock.advance(timedelta(seconds=600))
    assert _test(ana) == 200


def test_limit_is_per_user(users: Users, client: TestClient) -> None:
    users.use("ana")
    for _ in range(10):
        _test(client)
    assert _test(client) == 429
    users.use("bia")
    assert _test(client) == 200


def test_limit_and_window_from_env(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> None:
    """N e janela de `LLM_TEST_MAX_CALLS` e `LLM_TEST_WINDOW_SECONDS`."""
    monkeypatch.setenv("LLM_TEST_MAX_CALLS", "2")
    monkeypatch.setenv("LLM_TEST_WINDOW_SECONDS", "30")
    app = create_app(load_settings(env_file=None))
    clock = FakeClock(datetime(2026, 10, 23, 12, 0, tzinfo=UTC))
    app.state.clock = clock
    app.state.llm_adapters = {"openai": FakeAdapter()}
    with TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"}
    ) as client:
        Users(client).add("ana")
        assert [_test(client) for _ in range(3)] == [200, 200, 429]
        clock.advance(timedelta(seconds=30))
        assert _test(client) == 200


def test_429_logged_without_key(ana: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """SEC-20."""
    caplog.set_level(logging.DEBUG)
    for _ in range(11):
        _test(ana)
    [event] = [r for r in caplog.records if r.getMessage() == "security.rate_limited"]
    assert event.limiter == "llm_test"
    dumped = caplog.text + json.dumps([vars(r) for r in caplog.records], default=str)
    assert API_KEY not in dumped
