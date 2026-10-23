import logging

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

_INVALID_HOST_MESSAGE = "Host não permitido."
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


def install_http_security(app: FastAPI, settings: Settings) -> None:
    """Middlewares de borda. Sem CORS: app e API na mesma origem (SEC-14)."""
    # add_middleware põe na frente: o último registrado roda primeiro.
    app.add_middleware(AllowedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(SecurityHeadersMiddleware)
