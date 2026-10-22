from typing import Any

from fastapi import APIRouter, FastAPI

from snook.core.errors import register_error_handlers
from snook.core.settings import Settings, load_settings

health_router = APIRouter()


@health_router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Snook", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.settings = settings
    register_error_handlers(app)
    app.include_router(health_router)
    return app


def __getattr__(name: str) -> Any:
    """`uvicorn snook.main:app` cria a app na primeira leitura, não no import."""
    if name == "app":
        return create_app()
    raise AttributeError(name)
