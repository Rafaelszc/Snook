import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI

from snook.core.db import create_db_engine, create_session_factory, migrate_with_backup
from snook.core.errors import register_error_handlers
from snook.core.events import EventBus
from snook.core.http_security import SECURITY_HEADERS, install_http_security
from snook.core.runlock import RunLock
from snook.core.settings import Settings, load_settings

health_router = APIRouter()


@health_router.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _clear_tmp_dir(audio_root: Path) -> None:
    """Esvazia `/audios/.tmp/`. Link simbólico é removido, nunca seguido."""
    tmp = audio_root / ".tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    for entry in tmp.iterdir():
        if entry.is_dir() and not entry.is_symlink():
            shutil.rmtree(entry)
        else:
            entry.unlink()


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    # Sequência de subida de 02-architecture.md, "Retry e reinício".
    lock = RunLock(settings.database_path.with_name("snook.lock"))
    lock.acquire()  # 1
    try:
        migrate_with_backup(settings.database_path)  # 2
        _clear_tmp_dir(settings.audio_root)  # 3
        # 4 e 5 (marcar interrompidas, reenfileirar) entram na Task 21.2.
        engine = create_db_engine(settings.database_path)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.event_bus = EventBus()
        try:
            yield  # 7
        finally:
            engine.dispose()
    finally:
        lock.release()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(
        title="Snook",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    register_error_handlers(app, server_error_headers=SECURITY_HEADERS)
    install_http_security(app, settings)
    app.include_router(health_router)
    return app


def __getattr__(name: str) -> Any:
    """`uvicorn snook.main:app` cria a app na primeira leitura, não no import."""
    if name == "app":
        return create_app()
    raise AttributeError(name)
