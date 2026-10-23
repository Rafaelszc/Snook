from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.settings import Settings, SettingsError, load_settings
from snook.main import create_app
from tests.conftest import VALID_MASTER_KEY


def test_lan_host_extends_allowed_hosts_and_origins(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.casa.lan")
    s = load_settings(env_file=None)
    assert s.allowed_hosts == ["localhost", "127.0.0.1", "snook.casa.lan"]
    assert s.allowed_origins == [
        "http://localhost:8080",
        "http://127.0.0.1:8080",
        "https://snook.casa.lan",
    ]


def test_lan_host_accepts_ip(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "192.168.0.10")
    assert "192.168.0.10" in load_settings(env_file=None).allowed_hosts


def test_explicit_allowed_lists_replace_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.casa.lan")
    monkeypatch.setenv("ALLOWED_HOSTS", "a.example, b.example")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://a.example")
    s = load_settings(env_file=None)
    assert s.allowed_hosts == ["a.example", "b.example"]
    assert s.allowed_origins == ["https://a.example"]


@pytest.mark.parametrize(
    "bad_host",
    [
        "https://snook.lan",
        "snook.lan:8443",
        "snook.lan/path",
        "snook lan",
        "-snook.lan",
        "snook..lan",
        "999.1.1.1.1",
    ],
)
def test_invalid_lan_host_blocks_startup(monkeypatch: pytest.MonkeyPatch, bad_host: str) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", bad_host)
    with pytest.raises(SettingsError) as exc:
        load_settings(env_file=None)
    assert "SNOOK_LAN_HOST" in str(exc.value)


def test_empty_lan_host_is_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SNOOK_MASTER_KEY", VALID_MASTER_KEY)
    monkeypatch.setenv("SNOOK_LAN_HOST", "")
    assert load_settings(env_file=None).allowed_hosts == ["localhost", "127.0.0.1"]


@pytest.fixture
def lan_app(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> FastAPI:
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.casa.lan")
    return create_app(load_settings(env_file=None))


def _probe(app: FastAPI) -> FastAPI:
    @app.post("/api/_probe/write")
    def write() -> dict[str, bool]:
        return {"ok": True}

    return app


def test_lan_host_and_origin_pass_http_checks(lan_app: FastAPI) -> None:
    with TestClient(_probe(lan_app), base_url="https://snook.casa.lan") as client:
        assert client.get("/api/health").status_code == 200
        response = client.post("/api/_probe/write", headers={"Origin": "https://snook.casa.lan"})
        assert response.status_code == 200


def test_lan_origin_over_http_is_refused(lan_app: FastAPI) -> None:
    with TestClient(_probe(lan_app), base_url="https://snook.casa.lan") as client:
        response = client.post("/api/_probe/write", headers={"Origin": "http://snook.casa.lan"})
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "invalid_origin"


def test_caddyfile_sets_hsts_and_internal_tls() -> None:
    caddyfile = (Path(__file__).parents[3] / "deploy" / "Caddyfile").read_text()
    assert 'header Strict-Transport-Security "max-age=31536000"' in caddyfile
    assert "tls internal" in caddyfile
    assert "{$SNOOK_LAN_HOST}" in caddyfile
