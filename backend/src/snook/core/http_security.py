import contextlib
import logging
from urllib.parse import urlsplit

from fastapi import FastAPI
from starlette.datastructures import Headers
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from snook.core.errors import error_response
from snook.core.settings import Settings

logger = logging.getLogger("snook.security")

# SEC-13. HSTS fica no Caddy, só no perfil lan.
SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; img-src 'self' data:; media-src 'self' blob:; "
        "connect-src 'self'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; "
        "base-uri 'none'; form-action 'self'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), geolocation=(), microphone=(self), display-capture=(self)",
    "Cross-Origin-Opener-Policy": "same-origin",
}
_RAW_SECURITY_HEADERS = [
    (name.lower().encode("latin-1"), value.encode("latin-1"))
    for name, value in SECURITY_HEADERS.items()
]

JSON_BODY_MAX_BYTES = 1024 * 1024
# Upload em streaming, com limite próprio de UPLOAD_MAX_BYTES (ADR-0018).
_UPLOAD_ROUTES = {("POST", "/api/meetings")}
_STATE_CHANGING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}

_INVALID_HOST_MESSAGE = "Host não permitido."
_INVALID_ORIGIN_MESSAGE = "Origem da requisição não permitida."
_PAYLOAD_TOO_LARGE_MESSAGE = "Corpo da requisição grande demais."
_LOGGED_HOST_MAX = 100


class SecurityHeadersMiddleware:
    """Põe os headers de SEC-13 em toda resposta que passa por aqui."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                names = {name for name, _ in _RAW_SECURITY_HEADERS}
                kept = [(n, v) for n, v in message.get("headers", []) if n.lower() not in names]
                message["headers"] = kept + _RAW_SECURITY_HEADERS
            await send(message)

        await self.app(scope, receive, send_with_headers)


def _host_name(host_header: str) -> str:
    """Tira a porta do `Host`; aceita IPv6 entre colchetes."""
    if host_header.startswith("["):
        return host_header[1 : host_header.find("]")] if "]" in host_header else ""
    return host_header.rsplit(":", 1)[0] if ":" in host_header else host_header


class AllowedHostMiddleware:
    """SEC-14: `Host` fora de `ALLOWED_HOSTS` recebe 400 `invalid_host`, no formato da API."""

    def __init__(self, app: ASGIApp, allowed_hosts: list[str]) -> None:
        self.app = app
        self.allowed = {host.strip("[]").lower() for host in allowed_hosts}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        host = Headers(scope=scope).get("host", "")
        if _host_name(host).lower() in self.allowed:
            await self.app(scope, receive, send)
            return
        logger.warning("security.host_rejected", extra={"host": host[:_LOGGED_HOST_MAX]})
        response = error_response("invalid_host", _INVALID_HOST_MESSAGE, 400)
        await response(scope, receive, send)


def _request_origin(headers: Headers) -> str | None:
    """`Origin`; sem ele, esquema e host do `Referer`."""
    origin = headers.get("origin")
    if origin is not None:
        return origin
    referer = urlsplit(headers.get("referer", ""))
    if referer.scheme and referer.netloc:
        return f"{referer.scheme}://{referer.netloc}"
    return None


class OriginCheckMiddleware:
    """SEC-04: método que muda estado sem `Origin` em `ALLOWED_ORIGINS` recebe 403."""

    def __init__(self, app: ASGIApp, allowed_origins: list[str]) -> None:
        self.app = app
        self.allowed = {origin.rstrip("/").lower() for origin in allowed_origins}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["method"] not in _STATE_CHANGING_METHODS:
            await self.app(scope, receive, send)
            return
        origin = _request_origin(Headers(scope=scope))
        if origin is not None and origin.lower() in self.allowed:
            await self.app(scope, receive, send)
            return
        logger.warning(
            "security.origin_rejected", extra={"method": scope["method"], "path": scope["path"]}
        )
        response = error_response("invalid_origin", _INVALID_ORIGIN_MESSAGE, 403)
        await response(scope, receive, send)


class _BodyTooLarge(Exception):
    pass


class BodyLimitMiddleware:
    """SEC-25: corpo acima de 1 MiB recebe 413. O upload tem limite próprio (ADR-0018)."""

    def __init__(self, app: ASGIApp, max_bytes: int = JSON_BODY_MAX_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or (scope["method"], scope["path"]) in _UPLOAD_ROUTES:
            await self.app(scope, receive, send)
            return
        too_large = error_response("payload_too_large", _PAYLOAD_TOO_LARGE_MESSAGE, 413)
        declared = Headers(scope=scope).get("content-length", "")
        if declared.isdigit() and int(declared) > self.max_bytes:
            await too_large(scope, receive, send)
            return

        # Sem Content-Length confiável (chunked): conta o que chega.
        received = 0
        exceeded = False
        response_started = False

        async def counting_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    raise _BodyTooLarge
            return message

        async def guarded_send(message: Message) -> None:
            nonlocal response_started
            if exceeded and not response_started:
                return  # a resposta da app ao erro de leitura é trocada pelo 413
            response_started = response_started or message["type"] == "http.response.start"
            await send(message)

        with contextlib.suppress(_BodyTooLarge):
            await self.app(scope, counting_receive, guarded_send)
        if exceeded and not response_started:
            await too_large(scope, receive, send)


def install_http_security(app: FastAPI, settings: Settings) -> None:
    """Middlewares de borda. Sem CORS: app e API na mesma origem (SEC-14)."""
    # add_middleware põe na frente: o último registrado roda primeiro.
    app.add_middleware(BodyLimitMiddleware)
    app.add_middleware(OriginCheckMiddleware, allowed_origins=settings.allowed_origins)
    app.add_middleware(AllowedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(SecurityHeadersMiddleware)
