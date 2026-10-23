import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from snook.core.settings import Settings, load_settings
from snook.main import create_app

_NGINX = "172.28.0.10"
_CADDY = "172.28.0.11"
_LAN_CLIENT = "192.168.1.50"


def _app_with_probe(settings: Settings) -> FastAPI:
    """Rota que devolve IP e esquema resolvidos. Só existe na suíte, nunca na app de produção."""
    app = create_app(settings)

    @app.get("/api/_probe/client")
    def client_info(request: Request) -> dict[str, str]:
        assert request.client is not None
        return {"ip": request.client.host, "scheme": request.url.scheme}

    return app


def _resolve(settings: Settings, peer: str, headers: dict[str, str]) -> dict[str, str]:
    with TestClient(
        _app_with_probe(settings), base_url="http://localhost", client=(peer, 40000)
    ) as client:
        response = client.get("/api/_probe/client", headers=headers)
    assert response.status_code == 200
    result: dict[str, str] = response.json()
    return result


def test_trusted_proxy_resolves_first_untrusted_ip_from_the_right(settings: Settings) -> None:
    result = _resolve(settings, _NGINX, {"X-Forwarded-For": f"1.2.3.4, {_LAN_CLIENT}"})
    assert result["ip"] == _LAN_CLIENT


def test_chain_caddy_then_nginx_resolves_lan_client(settings: Settings) -> None:
    headers = {"X-Forwarded-For": f"1.2.3.4, {_LAN_CLIENT}, {_CADDY}"}
    assert _resolve(settings, _NGINX, headers)["ip"] == _LAN_CLIENT


def test_forwarded_proto_counts_from_trusted_proxy(settings: Settings) -> None:
    assert _resolve(settings, _NGINX, {"X-Forwarded-Proto": "https"})["scheme"] == "https"


def test_untrusted_peer_has_forwarded_headers_ignored(settings: Settings) -> None:
    peer = "192.168.1.99"
    headers = {"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Proto": "https"}
    assert _resolve(settings, peer, headers) == {"ip": peer, "scheme": "http"}


def test_trusted_list_comes_from_settings(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("TRUSTED_PROXY_IPS", "10.0.0.5")
    custom = load_settings(env_file=None)
    headers = {"X-Forwarded-For": "1.2.3.4", "X-Forwarded-Proto": "https"}
    assert _resolve(custom, _NGINX, headers) == {"ip": _NGINX, "scheme": "http"}
    assert _resolve(custom, "10.0.0.5", headers) == {"ip": "1.2.3.4", "scheme": "https"}
