from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings
from snook.main import create_app

_EXPECTED_HEADERS = {
    "content-security-policy": (
        "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
        "connect-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'self'"
    ),
    "x-content-type-options": "nosniff",
    "referrer-policy": "no-referrer",
    "permissions-policy": "camera=(), geolocation=(), microphone=(self), display-capture=(self)",
    "cross-origin-opener-policy": "same-origin",
}


def _app_with_boom(settings: Settings) -> FastAPI:
    app = create_app(settings)

    @app.get("/api/_probe/boom")
    def boom() -> None:
        raise RuntimeError("falha")

    return app


def _assert_security_headers(headers: dict[str, str]) -> None:
    for name, value in _EXPECTED_HEADERS.items():
        assert headers.get(name) == value, name
    assert "strict-transport-security" not in headers


def test_ok_response_has_security_headers_and_no_hsts(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    _assert_security_headers(dict(response.headers))


def test_not_found_has_security_headers(client: TestClient) -> None:
    response = client.get("/api/nao-existe")
    assert response.status_code == 404
    _assert_security_headers(dict(response.headers))


def test_unhandled_error_has_security_headers(settings: Settings) -> None:
    probe = TestClient(
        _app_with_boom(settings), base_url="http://localhost", raise_server_exceptions=False
    )
    response = probe.get("/api/_probe/boom")
    assert response.status_code == 500
    _assert_security_headers(dict(response.headers))


def test_foreign_host_gets_400_invalid_host(app: FastAPI) -> None:
    with TestClient(app, base_url="http://evil.example") as foreign:
        response = foreign.get("/api/health")
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_host"
    _assert_security_headers(dict(response.headers))


def test_allowed_host_with_port_passes(app: FastAPI) -> None:
    with TestClient(app, base_url="http://127.0.0.1:8000") as local:
        assert local.get("/api/health").status_code == 200


def test_missing_host_gets_400(client: TestClient) -> None:
    response = client.get("/api/health", headers={"Host": ""})
    assert response.status_code == 400


def test_no_cors_header_even_with_foreign_origin(client: TestClient) -> None:
    evil = {"Origin": "https://evil.example"}
    responses = [
        client.get("/api/health", headers=evil),
        client.options("/api/health", headers={**evil, "Access-Control-Request-Method": "POST"}),
        client.post("/api/health", headers=evil),
    ]
    for response in responses:
        assert not any(name.startswith("access-control-") for name in response.headers)
