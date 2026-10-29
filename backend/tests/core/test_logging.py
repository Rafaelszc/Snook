import json
import logging
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from snook.core.logging import register_secret, setup_logging
from snook.core.settings import Settings, load_settings
from snook.main import create_app
from tests.conftest import VALID_MASTER_KEY

_HF_TOKEN = "hf_TesteTokenConhecido123"
_LLM_KEY = "sk-ant-TesteChaveConhecida_456"
_PASSWORD = "senha-de-teste-Conhecida-789"
_SESSION_TOKEN = "TokenDeSessaoConhecido0123456789abcdef"
_SECRETS = [VALID_MASTER_KEY, _HF_TOKEN, _LLM_KEY, _PASSWORD, _SESSION_TOKEN]
_TRANSCRIPT_MARKER = "MARCADOR-TRANSCRICAO-7f3a"

log = logging.getLogger("snook.test")


@pytest.fixture
def secret_settings(settings: Settings, monkeypatch: pytest.MonkeyPatch) -> Settings:
    monkeypatch.setenv("HF_TOKEN", _HF_TOKEN)
    return load_settings(env_file=None)


def _json_lines(out: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in out.splitlines() if line.strip()]


def test_log_is_one_json_object_per_line(
    settings: Settings, capsys: pytest.CaptureFixture[str]
) -> None:
    setup_logging(settings)
    log.info("test.first", extra={"meeting_id": 7})
    log.warning("test.second")
    lines = _json_lines(capsys.readouterr().out)
    assert [line["event"] for line in lines] == ["test.first", "test.second"]
    assert lines[0]["level"] == "INFO"
    assert lines[0]["logger"] == "snook.test"
    assert lines[0]["meeting_id"] == 7
    assert {"ts", "request_id"} <= set(lines[0])


def test_log_level_comes_from_settings(
    settings: Settings, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("LOG_LEVEL", "warning")
    setup_logging(load_settings(env_file=None))
    log.info("test.hidden")
    log.warning("test.shown")
    assert [line["event"] for line in _json_lines(capsys.readouterr().out)] == ["test.shown"]


def test_known_secrets_never_appear_in_logs(
    secret_settings: Settings,
    caplog: pytest.LogCaptureFixture,
    capsys: pytest.CaptureFixture[str],
) -> None:
    setup_logging(secret_settings)
    register_secret(_PASSWORD)
    register_secret(_SESSION_TOKEN)
    with caplog.at_level(logging.INFO):
        log.info("test.secrets %s %s", VALID_MASTER_KEY, _HF_TOKEN)
        log.info("test.extra", extra={"detail": f"{_LLM_KEY} {_PASSWORD}"})
        log.info("test.bearer Authorization: Bearer %s", _SESSION_TOKEN)
        try:
            raise ValueError(f"falha com {_LLM_KEY} {_PASSWORD} {_SESSION_TOKEN}")
        except ValueError:
            log.exception("test.failure")
    out = capsys.readouterr().out
    lines = _json_lines(out)
    assert lines[-1]["error_type"] == "ValueError"
    for secret in _SECRETS:
        assert secret not in caplog.text
        assert secret not in out
    assert "[REDACTED]" in out


def test_llm_key_pattern_is_redacted_without_registration(
    settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    setup_logging(settings)
    with caplog.at_level(logging.INFO):
        log.info("test.pattern sk-ProjOutraChave12345 hf_OutroToken9876")
    assert "sk-ProjOutraChave12345" not in caplog.text
    assert "hf_OutroToken9876" not in caplog.text


def _app_with_probe(settings: Settings) -> FastAPI:
    app = create_app(settings)

    @app.post("/api/_probe/segments/{segment_id}")
    def save_segment(segment_id: int, body: dict[str, str]) -> dict[str, int]:
        return {"segment_id": segment_id}

    @app.post("/api/_probe/segments-boom")
    def boom(body: dict[str, str]) -> None:
        raise RuntimeError("falha interna")

    return app


def test_transcript_text_never_enters_logs(
    settings: Settings, caplog: pytest.LogCaptureFixture, capsys: pytest.CaptureFixture[str]
) -> None:
    text = {"text": f"fala do participante {_TRANSCRIPT_MARKER}"}
    caplog.set_level(logging.WARNING, logger="httpx")  # cliente do teste, não a app
    with (
        caplog.at_level(logging.DEBUG),
        TestClient(
            _app_with_probe(settings),
            base_url="http://localhost",
            headers={"Origin": "http://localhost:8080"},
            raise_server_exceptions=False,
        ) as client,
    ):
        assert client.post("/api/_probe/segments/1", json=text).status_code == 200
        assert (
            client.post(f"/api/_probe/segments/x?q={_TRANSCRIPT_MARKER}", json=text).status_code
            == 422
        )
        assert client.post("/api/_probe/segments-boom", json=text).status_code == 500
    assert _TRANSCRIPT_MARKER not in caplog.text
    out = capsys.readouterr().out
    assert _TRANSCRIPT_MARKER not in out
    error = next(line for line in _json_lines(out) if line["level"] == "ERROR")
    assert error["request_id"] is not None


def test_access_log_has_route_template_status_and_request_id(
    client: TestClient, capsys: pytest.CaptureFixture[str]
) -> None:
    capsys.readouterr()
    response = client.get("/api/health?x=1")
    access = [
        line for line in _json_lines(capsys.readouterr().out) if line["event"] == "http.request"
    ]
    assert len(access) == 1
    assert access[0]["method"] == "GET"
    assert access[0]["route"] == "/api/health"
    assert access[0]["status"] == 200
    assert isinstance(access[0]["duration_ms"], int | float)
    assert access[0]["request_id"] == response.headers["x-request-id"]


def test_uvicorn_access_log_is_off(settings: Settings) -> None:
    setup_logging(settings)
    assert logging.getLogger("uvicorn.access").disabled
