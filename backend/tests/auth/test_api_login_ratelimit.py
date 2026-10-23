import json
import logging
from datetime import timedelta
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings, load_settings
from snook.main import create_app
from tests.auth.helpers import PASSWORD, registration

_REGISTER = "/api/auth/register"
_LOGIN = "/api/auth/login"
_WRONG = "senha-errada-1"
_NGINX = "172.28.0.10"
_LAN_CLIENT = "192.168.1.50"


def _client(app: FastAPI, peer: str = "192.168.1.20") -> TestClient:
    return TestClient(
        app,
        base_url="http://localhost",
        headers={"Origin": "http://localhost:8080"},
        client=(peer, 40000),
    )


def _login(
    client: TestClient, identifier: str, password: str, headers: dict[str, str] | None = None
) -> Any:
    return client.post(
        _LOGIN, json={"identifier": identifier, "password": password}, headers=headers
    )


@pytest.fixture
def registered(app: FastAPI) -> None:
    with _client(app) as other:
        assert other.post(_REGISTER, json=registration()).status_code == 201


def _assert_rate_limited(response: Any) -> int:
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    retry_after = int(response.headers["Retry-After"])
    assert retry_after > 0
    return retry_after


@pytest.mark.usefixtures("registered")
def test_identifier_limit_blocks_even_correct_password(app: FastAPI, clock: FakeClock) -> None:
    """`auth` 27: 5 falhas no identificador, a 6ª tentativa leva 429 mesmo com senha certa."""
    with _client(app) as client:
        for _ in range(5):
            assert _login(client, "ana", _WRONG).status_code == 401
        retry_after = _assert_rate_limited(_login(client, "ana", PASSWORD))
        # Mesmo identificador normalizado: caixa e email não driblam o limite.
        _assert_rate_limited(_login(client, "ANA", PASSWORD))
    assert retry_after == 900


@pytest.mark.usefixtures("registered")
def test_window_passing_releases_login(app: FastAPI, clock: FakeClock) -> None:
    with _client(app) as client:
        for _ in range(5):
            _login(client, "ana", _WRONG)
        _assert_rate_limited(_login(client, "ana", PASSWORD))
        clock.advance(timedelta(seconds=900))
        assert _login(client, "ana", PASSWORD).status_code == 200


@pytest.mark.usefixtures("registered")
def test_successful_login_resets_identifier_count(app: FastAPI, clock: FakeClock) -> None:
    """`auth` 27: login correto antes do limite zera a contagem."""
    with _client(app) as client:
        for _ in range(4):
            _login(client, "ana", _WRONG)
        assert _login(client, "ana", PASSWORD).status_code == 200
        for _ in range(4):
            assert _login(client, "ana", _WRONG).status_code == 401
        assert _login(client, "ana", PASSWORD).status_code == 200


def test_ip_limit_after_20_failures(app: FastAPI, clock: FakeClock) -> None:
    """Abuse case: 21ª falha a partir de um IP leva 429, com identificadores diferentes."""
    with _client(app) as client:
        for i in range(20):
            assert _login(client, f"conta{i}", _WRONG).status_code == 401
        _assert_rate_limited(_login(client, "outra", _WRONG))
    with _client(app, peer="192.168.1.21") as other_ip:
        assert _login(other_ip, "outra", _WRONG).status_code == 401


def test_forged_forwarded_for_does_not_change_counted_ip(app: FastAPI, clock: FakeClock) -> None:
    """SEC-27: `X-Forwarded-For` direto ao backend é ignorado; o IP contado é o da conexão."""
    with _client(app) as client:
        for i in range(20):
            forged = {"X-Forwarded-For": f"10.0.0.{i}"}
            assert _login(client, f"conta{i}", _WRONG, forged).status_code == 401
        _assert_rate_limited(_login(client, "outra", _WRONG, {"X-Forwarded-For": "10.0.0.99"}))


def test_ip_behind_trusted_proxy_is_the_client(app: FastAPI, clock: FakeClock) -> None:
    """Atrás do nginx, conta o IP do cliente, não o do proxy."""
    with _client(app, peer=_NGINX) as client:
        for i in range(20):
            headers = {"X-Forwarded-For": _LAN_CLIENT}
            assert _login(client, f"conta{i}", _WRONG, headers).status_code == 401
        _assert_rate_limited(_login(client, "outra", _WRONG, {"X-Forwarded-For": _LAN_CLIENT}))
        other = {"X-Forwarded-For": "192.168.1.51"}
        assert _login(client, "outra", _WRONG, other).status_code == 401


def test_limits_come_from_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LOGIN_MAX_FAILURES", "2")
    monkeypatch.setenv("LOGIN_MAX_FAILURES_PER_IP", "3")
    monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "60")
    app = create_app(load_settings(env_file=None))
    with _client(app) as client:
        for _ in range(2):
            assert _login(client, "ana", _WRONG).status_code == 401
        assert _assert_rate_limited(_login(client, "ana", _WRONG)) <= 60
        assert _login(client, "bia", _WRONG).status_code == 401
        _assert_rate_limited(_login(client, "carla", _WRONG))


def _events(caplog: pytest.LogCaptureFixture, name: str) -> list[logging.LogRecord]:
    return [r for r in caplog.records if r.getMessage() == name]


@pytest.mark.usefixtures("registered")
def test_rate_limited_and_failures_are_logged_without_password(
    app: FastAPI, clock: FakeClock, caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20: `auth.login_failed` e `security.rate_limited` registrados, sem senha."""
    caplog.set_level(logging.DEBUG)
    with _client(app) as client:
        for _ in range(5):
            _login(client, "ana", _WRONG)
        _login(client, "ana", PASSWORD)

    failed = _events(caplog, "auth.login_failed")
    assert len(failed) == 5
    assert failed[0].levelno == logging.WARNING
    assert vars(failed[0])["reason"] == "bad_credentials"
    assert vars(failed[0])["ip"] == "192.168.1.20"

    limited = _events(caplog, "security.rate_limited")
    assert len(limited) == 1
    assert limited[0].levelno == logging.WARNING
    assert vars(limited[0])["limiter"] == "login_identifier"
    assert vars(limited[0])["ip"] == "192.168.1.20"

    dumped = caplog.text + json.dumps([vars(r) for r in caplog.records], default=str)
    assert PASSWORD not in dumped
    assert _WRONG not in dumped
