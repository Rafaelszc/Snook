import hashlib
from datetime import timedelta
from http.cookies import SimpleCookie

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.clock import FakeClock
from snook.core.settings import Settings, load_settings
from snook.main import create_app
from snook.modules.auth.deps import CurrentUser
from snook.modules.auth.service import AuthUser
from tests.auth.helpers import registration, rows

_REGISTER = "/api/auth/register"
_PROBE = "/api/_probe/me"


def _add_probe(app: FastAPI) -> None:
    """Rota protegida só da suíte; o `GET /auth/me` real vem na Task 10.1."""

    @app.get(_PROBE)
    def me(user: CurrentUser) -> dict[str, str]:
        assert isinstance(user, AuthUser)
        return {"id": user.id}


@pytest.fixture
def probe_app(app: FastAPI) -> FastAPI:
    _add_probe(app)
    return app


def _browser(app: FastAPI) -> TestClient:
    """Como o navegador: cookie `Secure` só volta por HTTPS, e `localhost` já o recebe."""
    return TestClient(
        app, base_url="https://localhost", headers={"Origin": "http://localhost:8080"}
    )


def _cookie(set_cookie: str) -> SimpleCookie:
    cookie: SimpleCookie = SimpleCookie()
    cookie.load(set_cookie)
    return cookie


def test_register_sets_session_cookie_flags(client: TestClient) -> None:
    """SEC-03: HttpOnly, SameSite=Lax, Path=/; Secure em localhost."""
    response = client.post(_REGISTER, json=registration())
    morsel = _cookie(response.headers["set-cookie"])["snook_session"]
    assert morsel["httponly"]
    assert morsel["samesite"].lower() == "lax"
    assert morsel["path"] == "/"
    assert morsel["secure"]


def test_cookie_not_secure_on_plain_http_lan_ip(settings: Settings) -> None:
    custom = settings.model_copy(update={"allowed_hosts": ["127.0.0.1"]})
    with TestClient(
        create_app(custom),
        base_url="http://127.0.0.1",
        headers={"Origin": "http://127.0.0.1:8080"},
    ) as client:
        response = client.post(_REGISTER, json=registration())
    assert not _cookie(response.headers["set-cookie"])["snook_session"]["secure"]


def test_cookie_secure_with_forwarded_proto_from_trusted_proxy(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SEC-03 + SEC-27: HTTPS resolvido pelo proxy confiável liga `Secure`."""
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.lan")
    lan = load_settings(env_file=None)
    with TestClient(
        create_app(lan),
        base_url="http://snook.lan",
        client=("172.28.0.10", 40000),
        headers={"Origin": "https://snook.lan", "X-Forwarded-Proto": "https"},
    ) as client:
        response = client.post(_REGISTER, json=registration())
    assert response.status_code == 201
    assert _cookie(response.headers["set-cookie"])["snook_session"]["secure"]


def test_forwarded_proto_from_untrusted_peer_is_ignored(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.lan")
    lan = load_settings(env_file=None)
    with TestClient(
        create_app(lan),
        base_url="http://snook.lan",
        client=("192.168.1.99", 40000),
        headers={"Origin": "http://localhost:8080", "X-Forwarded-Proto": "https"},
    ) as client:
        response = client.post(_REGISTER, json=registration())
    assert response.status_code == 201
    assert not _cookie(response.headers["set-cookie"])["snook_session"]["secure"]


def test_database_keeps_only_token_hash(client: TestClient, settings: Settings) -> None:
    """SEC-03; base de `auth` 8: o cadastro cria a sessão."""
    response = client.post(_REGISTER, json=registration())
    token = response.cookies["snook_session"]
    [(token_hash, user_id)] = rows(
        settings.database_path, "SELECT token_hash, user_id FROM sessions"
    )
    assert token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert user_id == response.json()["id"]
    assert token not in str(rows(settings.database_path, "SELECT * FROM sessions"))


def test_registration_session_reaches_protected_route(probe_app: FastAPI) -> None:
    with _browser(probe_app) as client:
        user_id = client.post(_REGISTER, json=registration()).json()["id"]
        assert client.get(_PROBE).json() == {"id": user_id}


def test_protected_route_without_cookie_is_401(probe_app: FastAPI) -> None:
    with TestClient(probe_app, base_url="http://localhost") as client:
        response = client.get(_PROBE)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_authenticated"


def test_unknown_token_is_401(probe_app: FastAPI) -> None:
    with TestClient(probe_app, base_url="http://localhost") as client:
        client.cookies.set("snook_session", "forjado")
        assert client.get(_PROBE).status_code == 401


def test_session_expires_after_24h_idle(probe_app: FastAPI, clock: FakeClock) -> None:
    with _browser(probe_app) as client:
        client.post(_REGISTER, json=registration())
        clock.advance(timedelta(hours=23, minutes=59))
        assert client.get(_PROBE).status_code == 200  # renova a inatividade
        clock.advance(timedelta(hours=23, minutes=59))
        assert client.get(_PROBE).status_code == 200
        clock.advance(timedelta(hours=24))
        assert client.get(_PROBE).status_code == 401


def test_session_expires_after_7_days_even_if_active(
    probe_app: FastAPI, clock: FakeClock, settings: Settings
) -> None:
    with _browser(probe_app) as client:
        client.post(_REGISTER, json=registration())
        for _ in range(13):
            clock.advance(timedelta(hours=12))
            assert client.get(_PROBE).status_code == 200
        clock.advance(timedelta(hours=12))  # 7 dias
        assert client.get(_PROBE).status_code == 401
    assert rows(settings.database_path, "SELECT COUNT(*) FROM sessions") == [(0,)]


def test_each_registration_gets_new_token(client: TestClient) -> None:
    first = client.post(_REGISTER, json=registration()).cookies["snook_session"]
    second = client.post(_REGISTER, json=registration(email="b@x.com", username="bob")).cookies[
        "snook_session"
    ]
    assert first != second


def test_startup_cleanup_removes_expired_sessions(
    settings: Settings, clock: FakeClock, app: FastAPI
) -> None:
    with TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"}
    ) as client:
        client.post(_REGISTER, json=registration())
    later = create_app(settings)
    later.state.clock = FakeClock(clock.now() + timedelta(days=2))
    with TestClient(later, base_url="http://localhost"):
        pass
    assert rows(settings.database_path, "SELECT COUNT(*) FROM sessions") == [(0,)]
