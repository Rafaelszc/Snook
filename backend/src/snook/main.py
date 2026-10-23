import asyncio
import logging
import shutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI

from snook.core.clock import SystemClock
from snook.core.db import create_db_engine, create_session_factory, migrate_with_backup
from snook.core.errors import register_error_handlers
from snook.core.events import EventBus
from snook.core.http_security import SECURITY_HEADERS, install_http_security
from snook.core.logging import RequestLogMiddleware, setup_logging
from snook.core.runlock import RunLock
from snook.core.settings import Settings, load_settings
from snook.core.uow import UnitOfWork
from snook.modules.auth import api as auth_api
from snook.modules.auth import service as auth_service
from snook.modules.llm_providers import api as llm_api
from snook.modules.llm_providers import service as llm_service
from snook.modules.meetings import api as meetings_api
from snook.modules.meetings import service as meetings_service

logger = logging.getLogger("snook.main")

SESSION_CLEANUP_SECONDS = 3600

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


def _cleanup_sessions(app: FastAPI) -> None:
    """Apaga sessões vencidas ou inativas (ADR-0008: no startup e a cada hora)."""
    state = app.state
    with UnitOfWork(state.session_factory, state.event_bus.publish) as uow:
        auth_service.delete_expired_sessions(
            uow, now=state.clock.now(), idle_seconds=state.settings.session_idle_seconds
        )


def _recover_meetings(app: FastAPI) -> None:
    """Marca interrompidas num commit, sem aviso; depois reenfileira `pending` (ADR-0007)."""
    state = app.state
    with UnitOfWork(state.session_factory, state.event_bus.publish) as uow:
        meetings_service.mark_interrupted(uow, now=state.clock.now())
    with UnitOfWork(state.session_factory, state.event_bus.publish) as uow:
        meetings_service.requeue_pending(uow)


async def _session_cleanup_loop(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(SESSION_CLEANUP_SECONDS)
        try:
            await asyncio.to_thread(_cleanup_sessions, app)
        except Exception:
            logger.exception("session cleanup failed")


@asynccontextmanager
async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    # Sequência de subida de 02-architecture.md, "Retry e reinício".
    lock = RunLock(settings.database_path.with_name("snook.lock"))
    lock.acquire()  # 1
    try:
        migrate_with_backup(settings.database_path)  # 2
        _clear_tmp_dir(settings.audio_root)  # 3
        engine = create_db_engine(settings.database_path)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        _recover_meetings(app)  # 4 e 5
        _cleanup_sessions(app)
        cleanup = asyncio.create_task(_session_cleanup_loop(app))
        try:
            yield  # 7
        finally:
            cleanup.cancel()
            engine.dispose()
    finally:
        lock.release()


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    setup_logging(settings)
    app = FastAPI(
        title="Snook",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_lifespan,
    )
    app.state.settings = settings
    app.state.clock = SystemClock()  # teste troca por FakeClock
    app.state.event_bus = EventBus()  # consumidores assinam antes da subida (reenfileirar)
    app.state.login_throttle = auth_service.LoginThrottle.from_settings(settings)
    app.state.key_cipher = llm_service.build_cipher(settings)
    app.state.llm_adapters = llm_service.build_adapters(settings)  # teste troca por fakes
    app.state.llm_test_limiter = llm_service.build_test_limiter(settings)
    app.state.media_probe = meetings_service.FfprobeProbe()  # teste troca por fake
    register_error_handlers(app, server_error_headers=SECURITY_HEADERS)
    install_http_security(app, settings)
    app.add_middleware(RequestLogMiddleware)  # por fora: loga também as rejeições
    app.include_router(health_router)
    app.include_router(auth_api.router)
    app.include_router(llm_api.router)
    app.include_router(meetings_api.router)
    return app


def __getattr__(name: str) -> Any:
    """`uvicorn snook.main:app` cria a app na primeira leitura, não no import."""
    if name == "app":
        return create_app()
    raise AttributeError(name)
