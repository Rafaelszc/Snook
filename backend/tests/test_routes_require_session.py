"""SEC-01 (transversal 10): toda rota em `/api` fora da lista pública exige sessão."""

import re

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute, iter_route_contexts
from fastapi.testclient import TestClient

PUBLIC = {
    ("GET", "/api/health"),
    ("POST", "/api/auth/register"),
    ("POST", "/api/auth/login"),
}


def _api_routes(app: FastAPI) -> list[tuple[str, str]]:
    # `app.routes` guarda routers incluídos aninhados; `iter_route_contexts` achata com prefixo.
    return sorted(
        (method, context.path)
        for context in iter_route_contexts(app.routes)
        if isinstance(context.original_route, APIRoute)
        and context.path
        and context.path.startswith("/api")
        for method in context.methods or ()
        if method != "HEAD"
    )


def _unprotected(app: FastAPI) -> list[tuple[str, str, int]]:
    """Rotas fora da lista pública que, sem cookie, não respondem 401."""
    found = []
    with TestClient(
        app, base_url="http://localhost", headers={"Origin": "http://localhost:8080"}
    ) as client:
        for method, path in _api_routes(app):
            if (method, path) in PUBLIC:
                continue
            url = re.sub(r"\{[^}]+\}", "00000000-0000-0000-0000-000000000000", path)
            status = client.request(method, url).status_code
            if status != 401:
                found.append((method, path, status))
    return found


def test_every_non_public_route_is_401_without_session(app: FastAPI) -> None:
    assert set(_api_routes(app)) >= PUBLIC
    assert _unprotected(app) == []


def test_scan_catches_route_without_session(app: FastAPI) -> None:
    router = APIRouter(prefix="/api/_leak")

    @router.get("/{item_id}")
    def leak(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    app.include_router(router)
    assert _unprotected(app) == [("GET", "/api/_leak/{item_id}", 200)]


def test_only_known_auth_routes_exist(app: FastAPI) -> None:
    """`auth` 21: sem recuperação, troca de senha, perfil ou exclusão de conta."""
    auth = {r for r in _api_routes(app) if r[1].startswith("/api/auth")}
    assert auth == {
        ("POST", "/api/auth/register"),
        ("POST", "/api/auth/login"),
        ("POST", "/api/auth/logout"),
        ("GET", "/api/auth/me"),
    }
