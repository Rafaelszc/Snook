from typing import Annotated

from fastapi import APIRouter, Depends, Request

from snook.core.clock import Clock
from snook.core.deps import get_clock, get_uow
from snook.core.errors import AppError
from snook.core.logging import register_secret
from snook.core.ratelimit import SlidingWindowLimiter
from snook.core.uow import UnitOfWork
from snook.modules.auth.deps import CurrentUser
from snook.modules.llm_providers import service
from snook.modules.llm_providers.adapters.base import LLMAdapter, LLMError
from snook.modules.llm_providers.crypto import KeyCipher
from snook.modules.llm_providers.schemas import ConfigDraft, ConfigOut, ConnectionResult, ModelList

router = APIRouter(prefix="/api/llm-configs")

# Rotas usam só o `user.id` da sessão; nada no caminho ou no corpo escolhe o Usuário (SEC-26).


def get_cipher(request: Request) -> KeyCipher:
    cipher: KeyCipher = request.app.state.key_cipher
    return cipher


def get_adapters(request: Request) -> dict[str, LLMAdapter]:
    """Teste troca por fakes em `app.state.llm_adapters`."""
    adapters: dict[str, LLMAdapter] = request.app.state.llm_adapters
    return adapters


def get_test_limiter(request: Request) -> SlidingWindowLimiter:
    limiter: SlidingWindowLimiter = request.app.state.llm_test_limiter
    return limiter


Uow = Annotated[UnitOfWork, Depends(get_uow)]
Cipher = Annotated[KeyCipher, Depends(get_cipher)]
Adapters = Annotated[dict[str, LLMAdapter], Depends(get_adapters)]
Limiter = Annotated[SlidingWindowLimiter, Depends(get_test_limiter)]
CurrentClock = Annotated[Clock, Depends(get_clock)]


def _attempt(
    uow: UnitOfWork, cipher: KeyCipher, user_id: str, provider: str, body: ConfigDraft
) -> service.ConnectionAttempt:
    service.require_provider(provider)
    if body.api_key is not None:
        register_secret(body.api_key)
    # Transação curta: a chamada ao provedor (até 20 s) fica fora dela.
    with uow:
        return service.resolve_attempt(uow, cipher, user_id=user_id, provider=provider, draft=body)


@router.get("")
def list_configs(user: CurrentUser, uow: Uow) -> list[ConfigOut]:
    with uow:
        return service.list_configs(uow, user_id=user.id)


@router.post("/{provider}/test")
def test_connection(
    provider: str,
    body: ConfigDraft,
    user: CurrentUser,
    uow: Uow,
    cipher: Cipher,
    adapters: Adapters,
    limiter: Limiter,
    clock: CurrentClock,
) -> ConnectionResult:
    """Não grava nada (`llm-providers` 5 a 9)."""
    attempt = _attempt(uow, cipher, user.id, provider, body)
    try:
        service.check_connection(
            attempt, adapters=adapters, limiter=limiter, user_id=user.id, now=clock.now()
        )
    except LLMError as exc:
        return ConnectionResult(ok=False, reason=service.reason_of(exc), message=exc.message)
    return ConnectionResult(ok=True)


@router.post("/{provider}/models")
def list_models(
    provider: str,
    body: ConfigDraft,
    user: CurrentUser,
    uow: Uow,
    cipher: Cipher,
    adapters: Adapters,
    limiter: Limiter,
    clock: CurrentClock,
) -> ModelList:
    """Modelos que a chave (do corpo ou a salva) enxerga. Não grava nada."""
    attempt = _attempt(uow, cipher, user.id, provider, body)
    try:
        models = service.list_models(
            attempt, adapters=adapters, limiter=limiter, user_id=user.id, now=clock.now()
        )
    except LLMError as exc:
        return ModelList(ok=False, reason=service.reason_of(exc), message=exc.message)
    return ModelList(ok=True, models=models)


@router.put("/{provider}")
def save_config(
    provider: str,
    body: ConfigDraft,
    user: CurrentUser,
    uow: Uow,
    cipher: Cipher,
    adapters: Adapters,
    limiter: Limiter,
    clock: CurrentClock,
) -> ConfigOut:
    """Refaz o teste no servidor; falha não muda nada (`llm-providers` 10 a 18)."""
    attempt = _attempt(uow, cipher, user.id, provider, body)
    try:
        service.check_connection(
            attempt, adapters=adapters, limiter=limiter, user_id=user.id, now=clock.now()
        )
    except LLMError as exc:
        raise AppError(service.reason_of(exc), exc.message, 422) from None
    with uow:
        return service.save_attempt(uow, cipher, attempt, user_id=user.id, now=clock.now())


@router.post("/{provider}/activate")
def activate_config(provider: str, user: CurrentUser, uow: Uow, clock: CurrentClock) -> ConfigOut:
    service.require_provider(provider)
    with uow:
        return service.activate_config(uow, user_id=user.id, provider=provider, now=clock.now())


@router.delete("/{provider}", status_code=204)
def delete_config(provider: str, user: CurrentUser, uow: Uow) -> None:
    service.require_provider(provider)
    with uow:
        service.delete_config(uow, user_id=user.id, provider=provider)
