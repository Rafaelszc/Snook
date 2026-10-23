from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from snook.core.clock import Clock
from snook.core.deps import get_clock, get_settings, get_uow
from snook.core.logging import register_secret
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.auth import service
from snook.modules.auth.deps import SESSION_COOKIE
from snook.modules.auth.schemas import RegisterRequest, UserOut

router = APIRouter(prefix="/api/auth")


def _cookie_secure(request: Request, settings: Settings) -> bool:
    """`auto`: liga em HTTPS (esquema já resolvido por SEC-27) e em `localhost` (SEC-03)."""
    if settings.session_cookie_secure != "auto":
        return settings.session_cookie_secure == "true"
    return request.url.scheme == "https" or request.url.hostname == "localhost"


def _set_session_cookie(
    response: Response, request: Request, settings: Settings, token: str
) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=settings.session_max_seconds,
        path="/",
        httponly=True,
        samesite="lax",
        secure=_cookie_secure(request, settings),
    )


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    uow: Annotated[UnitOfWork, Depends(get_uow)],
    settings: Annotated[Settings, Depends(get_settings)],
    clock: Annotated[Clock, Depends(get_clock)],
) -> UserOut:
    register_secret(body.password)
    now = clock.now()
    with uow:
        user = service.register_user(
            uow,
            email=body.email,
            username=body.username,
            password=body.password,
            rounds=settings.bcrypt_rounds,
            now=now,
        )
        # Login automático após o cadastro (ADR-0008).
        token = service.create_session(
            uow, user.id, now=now, max_seconds=settings.session_max_seconds
        )
    register_secret(token)
    _set_session_cookie(response, request, settings, token)
    return UserOut(id=user.id, email=user.email, username=user.username)
