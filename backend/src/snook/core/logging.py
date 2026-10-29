"""Logs JSON em stdout com redação de segredos (07-observability.md; SEC-20)."""

import json
import logging
import re
import sys
import time
import uuid
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from snook.core.settings import Settings

REDACTED = "[REDACTED]"
_PATTERNS = re.compile(r"sk-[A-Za-z0-9_-]{8,}|hf_[A-Za-z0-9]{8,}|Bearer\s+\S+")
_HANDLER_NAME = "snook-json"
# "color_message": cópia com ANSI que o uvicorn põe no registro.
_RECORD_FIELDS = set(vars(logging.makeLogRecord({}))) | {"message", "asctime", "color_message"}

_static_secrets: list[str] = []
_request_secrets: ContextVar[set[str] | None] = ContextVar("snook_request_secrets", default=None)
_request_id: ContextVar[str | None] = ContextVar("snook_request_id", default=None)

_base_record_factory = logging.getLogRecordFactory()
_access_logger = logging.getLogger("snook.http")


def register_secret(secret: str) -> None:
    """Segredo conhecido na requisição atual (senha, token, chave): sai como [REDACTED]."""
    if not secret:
        return
    secrets = _request_secrets.get()
    if secrets is None:
        secrets = set()
        _request_secrets.set(secrets)
    secrets.add(secret)


def redact(text: str) -> str:
    known = {*_static_secrets, *(_request_secrets.get() or ())}
    # O mais longo primeiro: um segredo que contém outro sai inteiro.
    for secret in sorted(known, key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    return _PATTERNS.sub(REDACTED, text)


def _redacting_record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
    # Redige na criação do registro: vale para todo handler, inclusive os de terceiros.
    # Campos de `extra` entram depois; o JsonFormatter os redige na saída.
    record = _base_record_factory(*args, **kwargs)
    try:
        record.msg = redact(record.getMessage())
        record.args = None
    except Exception:  # noqa: S110 - mensagem malformada segue como veio
        pass
    if record.exc_info and not record.exc_text:
        record.exc_text = redact(logging.Formatter().formatException(record.exc_info))
    return record


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
            "request_id": _request_id.get(),
        }
        entry.update(
            (key, value) for key, value in vars(record).items() if key not in _RECORD_FIELDS
        )
        if record.exc_info and record.exc_info[0] is not None:
            entry["error_type"] = record.exc_info[0].__name__
            entry["exc"] = record.exc_text or self.formatException(record.exc_info)
        return redact(json.dumps(entry, ensure_ascii=False, default=str))


class _StdoutHandler(logging.StreamHandler):  # type: ignore[type-arg]
    def emit(self, record: logging.LogRecord) -> None:
        # Lê sys.stdout a cada linha: quem captura a saída (pytest) troca o objeto.
        self.stream = sys.stdout
        super().emit(record)


def setup_logging(settings: Settings) -> None:
    """Idempotente: a app e a CLI chamam na subida."""
    _static_secrets[:] = [
        secret.get_secret_value()
        for secret in (
            settings.snook_master_key,
            settings.snook_master_key_previous,
            settings.hf_token,
        )
        if secret is not None and secret.get_secret_value()
    ]
    logging.setLogRecordFactory(_redacting_record_factory)

    root = logging.getLogger()
    for old in [h for h in root.handlers if h.get_name() == _HANDLER_NAME]:
        root.removeHandler(old)
    handler = _StdoutHandler()
    handler.set_name(_HANDLER_NAME)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)
    root.setLevel(settings.log_level)

    # uvicorn loga pelo root, em JSON. O log de acesso dele sai: quem loga é o middleware.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    logging.getLogger("uvicorn.access").disabled = True


class RequestLogMiddleware:
    """`request_id` por requisição, header `X-Request-ID` e log de acesso sem query."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        # Sem reset no fim: o 500 é logado por fora deste middleware e leva o id.
        # Cada requisição roda na própria task, com cópia do contexto: nada vaza.
        request_id = str(uuid.uuid4())
        _request_id.set(request_id)
        _request_secrets.set(set())
        status = 500
        started = time.perf_counter()

        async def send_with_id(message: Message) -> None:
            nonlocal status
            if message["type"] == "http.response.start":
                status = message["status"]
                headers = list(message.get("headers", []))
                message["headers"] = [*headers, (b"x-request-id", request_id.encode())]
            await send(message)

        try:
            await self.app(scope, receive, send_with_id)
        finally:
            route = getattr(scope.get("route"), "path", None) or "unmatched"
            _access_logger.info(
                "http.request",
                extra={
                    "method": scope["method"],
                    "route": route,
                    "status": status,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )
