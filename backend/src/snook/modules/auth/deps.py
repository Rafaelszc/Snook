from typing import Annotated

from fastapi import Depends, Request

from snook.core.clock import Clock
from snook.core.deps import get_clock, get_settings, get_uow
from snook.core.errors import AppError
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.auth import messages, service
from snook.modules.auth.service import AuthUser

SESSION_COOKIE = "snook_session"


def current_user(
    request: Request,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> AuthUser:
    """Usuário da sessão do cookie. Sem sessão válida: 401 antes da lógica da rota (SEC-01)."""
    token = request.cookies.get(SESSION_COOKIE)
    user = None
    if token:
        # Fora do raise: a sessão vencida apagada aqui precisa do commit.
        with uow:
            user = service.authenticate_session(
                uow, token, now=clock.now(), idle_seconds=settings.session_idle_seconds
            )
    if user is None:
        raise AppError("not_authenticated", messages.NOT_AUTHENTICATED, 401)
    return user


CurrentUser = Annotated[AuthUser, Depends(current_user)]
