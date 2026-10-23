import logging
from typing import Any

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.modules.auth import service
from tests.auth.helpers import PASSWORD, registration, rows

_REGISTER = "/api/auth/register"
_LOGIN = "/api/auth/login"
_LOGOUT = "/api/auth/logout"
_ME = "/api/auth/me"
_INVALID = "Email, nome de usuário ou senha inválidos."


def _browser(app: FastAPI) -> TestClient:
    """Como o navegador: cookie `Secure` só volta por HTTPS."""
    return TestClient(
        app, base_url="https://localhost", headers={"Origin": "http://localhost:8080"}
    )


@pytest.fixture
def registered(app: FastAPI) -> dict[str, Any]:
    """Usuário cadastrado por outro cliente: o teste começa sem sessão."""
    with _browser(app) as other:
        body: dict[str, Any] = other.post(_REGISTER, json=registration()).json()
    return body


@pytest.mark.parametrize("identifier", ["ana@x.com", "ana", "ANA@X.COM", "ANA", " ana "])
def test_login_authenticates(app: FastAPI, registered: dict[str, Any], identifier: str) -> None:
    """`auth` 12, 13, 14 e 20 (login sem sessão)."""
    with _browser(app) as client:
        response = client.post(_LOGIN, json={"identifier": identifier, "password": PASSWORD})
        assert response.status_code == 200
        assert response.json() == registered
        assert client.get(_ME).json() == registered


def test_login_sets_new_token(app: FastAPI, registered: dict[str, Any]) -> None:
    """SEC-03: token novo a cada login."""
    with _browser(app) as client:
        login = {"identifier": "ana", "password": PASSWORD}
        first = client.post(_LOGIN, json=login).cookies["snook_session"]
        second = client.post(_LOGIN, json=login).cookies["snook_session"]
    assert first != second


@pytest.mark.parametrize(
    ("identifier", "password"),
    [
        ("ana", "senha-errada-1"),
        ("bia@x.com", PASSWORD),
        ("bia", PASSWORD),
        ("ana", "x" * 73),
    ],
)
def test_login_failure_is_generic_401(
    app: FastAPI, registered: dict[str, Any], identifier: str, password: str
) -> None:
    """`auth` 15, 16; SEC-05: mesma mensagem para senha errada e conta inexistente."""
    with _browser(app) as client:
        response = client.post(_LOGIN, json={"identifier": identifier, "password": password})
        assert response.status_code == 401
        error = response.json()["error"]
        assert error["code"] == "invalid_credentials"
        assert error["message"] == _INVALID
        assert "set-cookie" not in response.headers
        assert client.get(_ME).status_code == 401


def test_unknown_account_still_pays_bcrypt(
    app: FastAPI, registered: dict[str, Any], monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-05: tempo parecido; conta inexistente também roda um `checkpw`."""
    calls: list[bytes] = []
    real = bcrypt.checkpw

    def spy(password: bytes, hashed: bytes) -> bool:
        calls.append(hashed)
        return real(password, hashed)

    monkeypatch.setattr(service.bcrypt, "checkpw", spy)
    with _browser(app) as client:
        client.post(_LOGIN, json={"identifier": "bia", "password": PASSWORD})
    assert len(calls) == 1
    assert calls[0].startswith(b"$2b$04$")  # mesmo custo do hash real


def test_login_rejects_extra_field(client: TestClient) -> None:
    """SEC-09."""
    response = client.post(_LOGIN, json={"identifier": "ana", "password": PASSWORD, "x": 1})
    assert response.status_code == 422


def test_login_without_origin_is_403(app: FastAPI, registered: dict[str, Any]) -> None:
    """SEC-04."""
    with TestClient(app, base_url="https://localhost") as client:
        response = client.post(_LOGIN, json={"identifier": "ana", "password": PASSWORD})
    assert response.status_code == 403


def test_login_password_not_logged(
    app: FastAPI, registered: dict[str, Any], caplog: pytest.LogCaptureFixture
) -> None:
    """SEC-20."""
    caplog.set_level(logging.DEBUG)
    with _browser(app) as client:
        token = client.post(_LOGIN, json={"identifier": "ana", "password": PASSWORD}).cookies[
            "snook_session"
        ]
        client.post(_LOGIN, json={"identifier": "ana", "password": "senha-errada-1"})
    assert PASSWORD not in caplog.text
    assert "senha-errada-1" not in caplog.text
    assert token not in caplog.text


def test_register_then_me_without_login(app: FastAPI) -> None:
    """`auth` 8 e 18: sem senha nem hash."""
    with _browser(app) as client:
        created = client.post(_REGISTER, json=registration()).json()
        response = client.get(_ME)
    assert response.status_code == 200
    assert response.json() == created
    assert set(response.json()) == {"id", "email", "username"}


def test_me_without_session_is_401(client: TestClient) -> None:
    """`auth` 19."""
    response = client.get(_ME)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_logout_deletes_session(app: FastAPI, settings: Settings) -> None:
    """`auth` 17; SEC-03: logout apaga a sessão no servidor."""
    with _browser(app) as client:
        client.post(_REGISTER, json=registration())
        token = client.cookies["snook_session"]
        response = client.post(_LOGOUT)
        assert response.status_code == 204
        assert 'snook_session=""' in response.headers["set-cookie"]
        assert rows(settings.database_path, "SELECT COUNT(*) FROM sessions") == [(0,)]
        # Mesmo token reenviado, como um cookie copiado antes do logout.
        client.cookies.set("snook_session", token)
        assert client.get(_ME).status_code == 401


def test_logout_keeps_other_sessions(app: FastAPI, registered: dict[str, Any]) -> None:
    # Um cliente só (a trava de execução não deixa dois lifespans); troca o cookie à mão.
    with _browser(app) as client:
        login = {"identifier": "ana", "password": PASSWORD}
        other = client.post(_LOGIN, json=login).cookies["snook_session"]
        client.post(_LOGIN, json=login)
        client.post(_LOGOUT)
        client.cookies.set("snook_session", other)
        assert client.get(_ME).status_code == 200


def test_logout_without_session_is_401(client: TestClient) -> None:
    assert client.post(_LOGOUT).status_code == 401
