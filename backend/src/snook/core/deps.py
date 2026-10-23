from fastapi import Request

from snook.core.clock import Clock
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_clock(request: Request) -> Clock:
    clock: Clock = request.app.state.clock
    return clock


def get_uow(request: Request) -> UnitOfWork:
    """Unidade de trabalho da requisição; a rota abre a transação com `with uow:`."""
    state = request.app.state
    return UnitOfWork(state.session_factory, state.event_bus.publish)
