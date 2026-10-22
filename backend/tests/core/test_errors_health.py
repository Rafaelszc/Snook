import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from snook.core.errors import AppError
from snook.core.settings import Settings
from snook.main import create_app


class _Payload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str


def _app_with_probe_routes(settings: Settings) -> FastAPI:
    app = create_app(settings)

    @app.get("/api/_probe/app-error")
    def app_error() -> None:
        raise AppError("meeting_not_found", "Reunião não encontrada.", 404)

    @app.get("/api/_probe/app-error-fields")
    def app_error_fields() -> None:
        raise AppError("conflict", "Conflito.", 409, fields={"title": "Duplicado."})

    @app.get("/api/_probe/boom")
    def boom() -> None:
        raise RuntimeError("segredo-interno /etc/passwd")

    @app.post("/api/_probe/payload")
    def payload(body: _Payload) -> dict[str, str]:
        return {"title": body.title}

    return app


@pytest.fixture
def probe(settings: Settings) -> TestClient:
    return TestClient(_app_with_probe_routes(settings), raise_server_exceptions=False)


def test_health_is_ok_without_session(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_app_error_becomes_standard_body(probe: TestClient) -> None:
    response = probe.get("/api/_probe/app-error")
    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "meeting_not_found", "message": "Reunião não encontrada."}
    }


def test_app_error_can_carry_fields(probe: TestClient) -> None:
    response = probe.get("/api/_probe/app-error-fields")
    assert response.status_code == 409
    assert response.json()["error"]["fields"] == {"title": "Duplicado."}


def test_unhandled_exception_is_generic_500_without_trace(
    probe: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    with caplog.at_level(logging.ERROR):
        response = probe.get("/api/_probe/boom")
    assert response.status_code == 500
    assert response.json() == {"error": {"code": "internal_error", "message": "erro interno"}}
    assert "segredo-interno" not in response.text
    assert "Traceback" not in response.text


def test_validation_error_is_422_with_fields_and_no_input_echo(probe: TestClient) -> None:
    response = probe.post("/api/_probe/payload", json={"title": 123, "extra": "valor-secreto"})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    assert set(error["fields"]) == {"title", "extra"}
    assert "valor-secreto" not in response.text


def test_missing_field_message_is_pt_br(probe: TestClient) -> None:
    response = probe.post("/api/_probe/payload", json={})
    assert response.json()["error"]["fields"] == {"title": "Campo obrigatório."}


def test_unknown_route_uses_standard_body(client: TestClient) -> None:
    response = client.get("/api/nao-existe")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_docs_and_openapi_are_not_exposed(client: TestClient) -> None:
    for path in ("/docs", "/redoc", "/openapi.json"):
        assert client.get(path).status_code == 404
