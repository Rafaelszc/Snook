import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.routing import iter_route_contexts
from fastapi.testclient import TestClient

from snook.core.settings import Settings, load_settings
from snook.main import create_app

_STATE_CHANGING = ["POST", "PUT", "PATCH", "DELETE"]
_ONE_MIB = 1024 * 1024


def _app_with_probe(settings: Settings) -> FastAPI:
    app = create_app(settings)

    @app.api_route("/api/_probe/write", methods=_STATE_CHANGING)
    def write() -> dict[str, bool]:
        return {"ok": True}

    @app.post("/api/_probe/json")
    def json_body(body: dict[str, Any]) -> dict[str, int]:
        return {"keys": len(body)}

    return app


@pytest.fixture
def probe(settings: Settings) -> Iterator[TestClient]:
    with TestClient(_app_with_probe(settings), base_url="http://localhost") as test_client:
        yield test_client


@pytest.mark.parametrize("method", _STATE_CHANGING)
def test_state_changing_without_origin_gets_403(probe: TestClient, method: str) -> None:
    response = probe.request(method, "/api/_probe/write")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_origin"


@pytest.mark.parametrize("method", _STATE_CHANGING)
def test_state_changing_with_foreign_origin_gets_403(probe: TestClient, method: str) -> None:
    response = probe.request(
        method, "/api/_probe/write", headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "invalid_origin"


@pytest.mark.parametrize("method", _STATE_CHANGING)
def test_state_changing_with_allowed_origin_passes(probe: TestClient, method: str) -> None:
    response = probe.request(
        method, "/api/_probe/write", headers={"Origin": "http://localhost:8080"}
    )
    assert response.status_code == 200


@pytest.mark.parametrize(
    ("referer", "status"),
    [
        ("http://localhost:8080/meetings/1", 200),
        ("https://evil.example/http://localhost:8080", 403),
    ],
)
def test_referer_is_used_when_origin_is_missing(
    probe: TestClient, referer: str, status: int
) -> None:
    response = probe.post("/api/_probe/write", headers={"Referer": referer})
    assert response.status_code == status


def test_null_origin_gets_403(probe: TestClient) -> None:
    response = probe.post(
        "/api/_probe/write", headers={"Origin": "null", "Referer": "http://localhost:8080/"}
    )
    assert response.status_code == 403


def test_lan_origin_passes_when_lan_host_is_set(
    settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SNOOK_LAN_HOST", "snook.lan")
    lan = load_settings(env_file=None)
    with TestClient(_app_with_probe(lan), base_url="https://snook.lan") as client:
        response = client.post("/api/_probe/write", headers={"Origin": "https://snook.lan"})
    assert response.status_code == 200


def test_get_without_origin_passes(probe: TestClient) -> None:
    assert probe.get("/api/health").status_code == 200


def _db_snapshot(db: Path) -> list[str]:
    with sqlite3.connect(db) as conn:
        return list(conn.iterdump())


def test_no_get_route_changes_the_database(app: FastAPI, settings: Settings) -> None:
    get_paths = [
        route.path
        for route in iter_route_contexts(app.routes)
        if route.path and route.methods and "GET" in route.methods and "{" not in route.path
    ]
    assert get_paths
    with TestClient(app, base_url="http://localhost") as client:
        before = _db_snapshot(settings.database_path)
        for path in get_paths:
            client.get(path)
        assert _db_snapshot(settings.database_path) == before


def _json_of_size(size: int) -> bytes:
    prefix, suffix = b'{"a":"', b'"}'
    return prefix + b"x" * (size - len(prefix) - len(suffix)) + suffix


def test_json_body_at_limit_passes(settings: Settings) -> None:
    with TestClient(
        _app_with_probe(settings),
        base_url="http://localhost",
        headers={"Origin": "http://localhost:8080"},
    ) as probe:
        response = probe.post(
            "/api/_probe/json",
            content=_json_of_size(_ONE_MIB),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 200


def test_json_body_over_limit_gets_413(settings: Settings) -> None:
    with TestClient(
        _app_with_probe(settings),
        base_url="http://localhost",
        headers={"Origin": "http://localhost:8080"},
    ) as probe:
        response = probe.post(
            "/api/_probe/json",
            content=_json_of_size(_ONE_MIB + 1),
            headers={"Content-Type": "application/json"},
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_chunked_body_over_limit_gets_413(settings: Settings) -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"a":"'
        for _ in range(17):
            yield b"x" * 65536
        yield b'"}'

    with TestClient(
        _app_with_probe(settings),
        base_url="http://localhost",
        headers={"Origin": "http://localhost:8080"},
    ) as probe:
        response = probe.post(
            "/api/_probe/json", content=chunks(), headers={"Content-Type": "application/json"}
        )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "payload_too_large"


def test_upload_route_is_not_held_to_json_limit(client: TestClient) -> None:
    response = client.post(
        "/api/meetings",
        content=b"x" * (_ONE_MIB + 1),
        headers={"Content-Type": "multipart/form-data; boundary=x"},
    )
    assert response.status_code != 413
