import logging
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from snook.core.clock import to_iso
from snook.core.errors import AppError
from snook.core.logging import register_secret
from snook.core.ratelimit import SlidingWindowLimiter
from snook.core.settings import Settings
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers import messages, repository
from snook.modules.llm_providers.adapters.anthropic import AnthropicAdapter

# Erros do contrato saem por aqui: consumidores importam só `service` (SEC-26).
from snook.modules.llm_providers.adapters.base import (
    ContextLimitExceeded as ContextLimitExceeded,
)
from snook.modules.llm_providers.adapters.base import (
    CredentialRejected as CredentialRejected,
)
from snook.modules.llm_providers.adapters.base import (
    GenerationRequest,
    LLMAdapter,
    ProviderTarget,
)
from snook.modules.llm_providers.adapters.base import LLMError as LLMError
from snook.modules.llm_providers.adapters.base import ModelNotFound as ModelNotFound
from snook.modules.llm_providers.adapters.base import NoActiveProvider as NoActiveProvider
from snook.modules.llm_providers.adapters.base import (
    ProviderRateLimited as ProviderRateLimited,
)
from snook.modules.llm_providers.adapters.base import (
    ProviderUnreachable as ProviderUnreachable,
)
from snook.modules.llm_providers.adapters.ollama import (
    InvalidBaseUrl,
    OllamaAdapter,
    normalize_base_url,
)
from snook.modules.llm_providers.adapters.openai_compat import OpenAICompatAdapter
from snook.modules.llm_providers.crypto import (
    KeyCipher,
    MasterKeyMismatch,
    SealedKey,
    decode_master_key,
)
from snook.modules.llm_providers.defaults import DEFAULTS
from snook.modules.llm_providers.models import (
    KEY_STATUS_OK,
    KEY_STATUS_UNREADABLE,
    PROVIDERS,
    LlmConfig,
)
from snook.modules.llm_providers.schemas import ConfigDraft, ConfigOut
from snook.modules.llm_providers.tokens import estimate_tokens as estimate_tokens

logger = logging.getLogger("snook.llm_providers")

MASK_MIN_LENGTH = 12


def mask_key(api_key: str) -> str:
    """3 primeiros e 4 últimos caracteres; chave com menos de 12 vira `...` (ADR-0005)."""
    if len(api_key) < MASK_MIN_LENGTH:
        return "..."
    return f"{api_key[:3]}...{api_key[-4:]}"


def _sealed(config: LlmConfig) -> SealedKey | None:
    if config.key_ciphertext is None or config.key_nonce is None or config.key_version is None:
        return None
    return SealedKey(
        ciphertext=config.key_ciphertext, nonce=config.key_nonce, version=config.key_version
    )


def _store_key(config: LlmConfig, cipher: KeyCipher, api_key: str) -> None:
    sealed = cipher.encrypt(api_key, user_id=config.user_id, provider=config.provider)
    config.key_ciphertext = sealed.ciphertext
    config.key_nonce = sealed.nonce
    config.key_version = sealed.version
    config.key_mask = mask_key(api_key)
    config.key_status = KEY_STATUS_OK


def save_config(
    uow: UnitOfWork,
    cipher: KeyCipher,
    *,
    user_id: str,
    provider: str,
    model: str,
    context_window: int,
    api_key: str | None,
    base_url: str | None,
    now: datetime,
) -> LlmConfig:
    """Cria ou atualiza a configuração. `api_key=None` mantém a chave gravada."""
    config = repository.get_config(uow.session, user_id, provider)
    if config is None:
        config = LlmConfig(
            user_id=user_id,
            provider=provider,
            key_status=KEY_STATUS_OK,
            is_active=False,
            created_at=to_iso(now),
        )
    config.model = model
    config.context_window = context_window
    config.base_url = base_url
    config.updated_at = to_iso(now)
    if api_key is not None:
        _store_key(config, cipher, api_key)
    repository.add_config(uow.session, config)
    return config


def read_api_key(uow: UnitOfWork, cipher: KeyCipher, *, user_id: str, provider: str) -> str | None:
    """Chave em texto claro, só para a chamada ao provedor.

    `None` sem chave ou com chave ilegível; ilegível fica marcada `unreadable` (ADR-0009).
    """
    config = repository.get_config(uow.session, user_id, provider)
    sealed = None if config is None else _sealed(config)
    if config is None or sealed is None:
        return None
    try:
        return cipher.decrypt(sealed, user_id=user_id, provider=provider)
    except MasterKeyMismatch:
        config.key_status = KEY_STATUS_UNREADABLE
        return None


@dataclass(frozen=True)
class RotationResult:
    rotated: int
    unreadable: int


def rotate_master_key(uow: UnitOfWork, cipher: KeyCipher, *, now: datetime) -> RotationResult:
    """Recifra toda chave com a chave-mestra atual (ADR-0009).

    Decifra com a atual ou a anterior. Chave que não decifra fica `unreadable`; nada é apagado.
    """
    rotated = unreadable = 0
    for config in repository.list_configs_with_key(uow.session):
        sealed = _sealed(config)
        if sealed is None:
            continue
        try:
            api_key = cipher.decrypt(sealed, user_id=config.user_id, provider=config.provider)
        except MasterKeyMismatch:
            config.key_status = KEY_STATUS_UNREADABLE
            unreadable += 1
            continue
        _store_key(config, cipher, api_key)
        config.updated_at = to_iso(now)
        rotated += 1
    return RotationResult(rotated=rotated, unreadable=unreadable)


# --- Configurações do Usuário (`/api/llm-configs`) ---

KEY_PROVIDERS = ("openai", "anthropic", "deepseek")

_REASONS = {
    "credential_rejected": "credential_rejected",
    "provider_unreachable": "provider_unreachable",
    "model_not_found": "model_not_found",
    "provider_rate_limited": "rate_limited",
    "context_limit_exceeded": "context_limit",
}


def build_cipher(settings: Settings) -> KeyCipher:
    previous = settings.snook_master_key_previous
    return KeyCipher(
        decode_master_key(settings.snook_master_key.get_secret_value()),
        previous=None if previous is None else decode_master_key(previous.get_secret_value()),
    )


def build_adapters(settings: Settings) -> dict[str, LLMAdapter]:
    timeout = float(settings.llm_read_timeout)
    return {
        "openai": OpenAICompatAdapter("openai", read_timeout=timeout),
        "anthropic": AnthropicAdapter(read_timeout=timeout),
        "deepseek": OpenAICompatAdapter("deepseek", read_timeout=timeout),
        "ollama": OllamaAdapter(read_timeout=timeout),
    }


def build_test_limiter(settings: Settings) -> SlidingWindowLimiter:
    """Teste e salvar dividem o limite, por Usuário (ADR-0010)."""
    return SlidingWindowLimiter(
        max_events=settings.llm_test_max_calls, window_seconds=settings.llm_test_window_seconds
    )


def require_provider(provider: str) -> None:
    if provider not in PROVIDERS:
        raise AppError("provider_not_found", messages.PROVIDER_NOT_FOUND, 404)


def reason_of(error: LLMError) -> str:
    return _REASONS.get(error.kind, "provider_unreachable")


def _field_error(field_name: str, message: str) -> AppError:
    return AppError("validation_error", messages.INVALID_DATA, 422, fields={field_name: message})


def _view(provider: str, config: LlmConfig | None) -> ConfigOut:
    default = DEFAULTS[provider]
    base = {
        "provider": provider,
        "default_model": default.model,
        "default_context_window": default.context_window,
    }
    if config is None:
        return ConfigOut(
            **base,
            state="not_configured",
            model=None,
            context_window=None,
            key_mask=None,
            base_url=None,
            key_status=None,
        )
    return ConfigOut(
        **base,
        state="active" if config.is_active else "configured",
        model=config.model,
        context_window=config.context_window,
        key_mask=config.key_mask,
        base_url=config.base_url,
        key_status=config.key_status,
    )


def list_configs(uow: UnitOfWork, *, user_id: str) -> list[ConfigOut]:
    """Os quatro provedores, configurados ou não (`llm-providers` 1 a 4)."""
    saved = {c.provider: c for c in repository.list_user_configs(uow.session, user_id)}
    return [_view(provider, saved.get(provider)) for provider in PROVIDERS]


@dataclass(frozen=True)
class ConnectionAttempt:
    """Valores do teste: corpo, senão o salvo, senão o padrão. `new_api_key`: chave a gravar."""

    provider: str
    target: ProviderTarget
    new_api_key: str | None = field(default=None, repr=False)
    key_unreadable: bool = False


def _resolve_base_url(draft: ConfigDraft, config: LlmConfig | None) -> str:
    base_url = draft.base_url or (config.base_url if config else None)
    if base_url is None:
        raise _field_error("base_url", messages.BASE_URL_REQUIRED)
    try:
        return normalize_base_url(base_url)
    except InvalidBaseUrl as exc:
        raise AppError(exc.code, exc.message, 422, fields={"base_url": exc.message}) from None


def resolve_attempt(
    uow: UnitOfWork, cipher: KeyCipher, *, user_id: str, provider: str, draft: ConfigDraft
) -> ConnectionAttempt:
    """Monta o alvo do teste. Chave salva só decifra aqui, sem sair do módulo (SEC-07)."""
    config = repository.get_config(uow.session, user_id, provider)
    default = DEFAULTS[provider]
    model = draft.model or (config.model if config else default.model)
    window = draft.context_window or (config.context_window if config else default.context_window)
    if provider == "ollama":
        if draft.api_key is not None:
            raise _field_error("api_key", messages.API_KEY_NOT_ALLOWED)
        target = ProviderTarget(
            model=model, base_url=_resolve_base_url(draft, config), context_window=window
        )
        return ConnectionAttempt(provider, target)
    if draft.base_url is not None:
        raise _field_error("base_url", messages.BASE_URL_NOT_ALLOWED)
    if draft.api_key is not None:
        target = ProviderTarget(model=model, api_key=draft.api_key, context_window=window)
        return ConnectionAttempt(provider, target, new_api_key=draft.api_key)
    if config is None or config.key_ciphertext is None:
        raise _field_error("api_key", messages.API_KEY_REQUIRED)
    # Ilegível fica `unreadable` no commit deste bloco; o teste falha depois (ADR-0009).
    saved_key = read_api_key(uow, cipher, user_id=user_id, provider=provider)
    if saved_key is not None:
        register_secret(saved_key)
    target = ProviderTarget(model=model, api_key=saved_key, context_window=window)
    return ConnectionAttempt(provider, target, key_unreadable=saved_key is None)


def check_connection(
    attempt: ConnectionAttempt,
    *,
    adapters: Mapping[str, LLMAdapter],
    limiter: SlidingWindowLimiter,
    user_id: str,
    now: datetime,
) -> None:
    """Chama o provedor fora de transação. Falha vira `LLMError`; acima do limite, 429."""
    if attempt.key_unreadable:
        raise CredentialRejected("unreadable_key")
    retry_after = limiter.retry_after(user_id, now)
    if retry_after:
        logger.warning("security.rate_limited", extra={"limiter": "llm_test", "user_id": user_id})
        raise AppError(
            "rate_limited", messages.RATE_LIMITED, 429, headers={"Retry-After": str(retry_after)}
        )
    limiter.hit(user_id, now)
    adapters[attempt.provider].test_connection(attempt.target)


def save_attempt(
    uow: UnitOfWork,
    cipher: KeyCipher,
    attempt: ConnectionAttempt,
    *,
    user_id: str,
    now: datetime,
) -> ConfigOut:
    """Grava o que passou no teste. Primeira do Usuário fica ativa (`llm-providers` 16)."""
    provider = attempt.provider
    existing = repository.get_config(uow.session, user_id, provider)
    if (
        provider in KEY_PROVIDERS
        and attempt.new_api_key is None
        and (existing is None or existing.key_ciphertext is None)
    ):
        # Removida entre o teste e a gravação: sem chave para manter.
        raise _field_error("api_key", messages.API_KEY_REQUIRED)
    first = not repository.list_user_configs(uow.session, user_id)
    target = attempt.target
    config = save_config(
        uow,
        cipher,
        user_id=user_id,
        provider=provider,
        model=target.model,
        context_window=target.context_window or DEFAULTS[provider].context_window,
        api_key=attempt.new_api_key,
        base_url=target.base_url,
        now=now,
    )
    if first:
        config.is_active = True
        uow.session.flush()
    logger.info("llm_config.saved", extra={"user_id": user_id, "provider": provider})
    return _view(provider, config)


def activate_config(uow: UnitOfWork, *, user_id: str, provider: str, now: datetime) -> ConfigOut:
    """Um ativo por Usuário (`llm-providers` 19 a 21)."""
    config = repository.get_config(uow.session, user_id, provider)
    if config is None:
        raise AppError("provider_not_configured", messages.PROVIDER_NOT_CONFIGURED, 409)
    current = repository.get_active_config(uow.session, user_id)
    if current is not None and current is not config:
        current.is_active = False
        current.updated_at = to_iso(now)
        # Antes de ativar o novo: o índice único parcial olha linha a linha.
        uow.session.flush()
    if not config.is_active:
        config.is_active = True
        config.updated_at = to_iso(now)
        uow.session.flush()
    logger.info("llm_config.activated", extra={"user_id": user_id, "provider": provider})
    return _view(provider, config)


def delete_config(uow: UnitOfWork, *, user_id: str, provider: str) -> None:
    """Apaga a linha e a chave cifrada; sem ativar outro (`llm-providers` 23 a 25)."""
    config = repository.get_config(uow.session, user_id, provider)
    if config is None:
        raise AppError("config_not_found", messages.CONFIG_NOT_FOUND, 404)
    repository.delete_config(uow.session, config)
    logger.info("llm_config.deleted", extra={"user_id": user_id, "provider": provider})


# --- Interface para outros módulos (`02-architecture.md`, "Interfaces internas") ---


@dataclass(frozen=True)
class ActiveProvider:
    """Provedor ativo lido uma vez por geração. Sem chave (SEC-07)."""

    provider: str
    model: str
    context_window: int


def get_active_provider(uow: UnitOfWork, *, user_id: str) -> ActiveProvider:
    """Provedor, modelo e janela do Usuário; sem ativo, `NoActiveProvider` (`llm-providers` 22)."""
    config = repository.get_active_config(uow.session, user_id)
    if config is None:
        raise NoActiveProvider("no_active_provider")
    return ActiveProvider(
        provider=config.provider, model=config.model, context_window=config.context_window
    )


def _generation_target(
    uow: UnitOfWork, cipher: KeyCipher, *, user_id: str, snapshot: ActiveProvider
) -> ProviderTarget | None:
    """Alvo com a chave do dono. `None` sem a configuração do snapshot."""
    config = repository.get_config(uow.session, user_id, snapshot.provider)
    if config is None:
        return None
    api_key = None
    if snapshot.provider in KEY_PROVIDERS:
        api_key = read_api_key(uow, cipher, user_id=user_id, provider=snapshot.provider)
    return ProviderTarget(
        model=snapshot.model,
        api_key=api_key,
        base_url=config.base_url,
        context_window=snapshot.context_window,
    )


def generate(
    uow: UnitOfWork,
    cipher: KeyCipher,
    adapters: Mapping[str, LLMAdapter],
    *,
    user_id: str,
    provider_snapshot: ActiveProvider,
    system_prompt: str,
    content: str,
    json_schema: dict[str, Any],
    max_output_tokens: int,
) -> str:
    """Texto da resposta do provedor do snapshot, com a configuração do dono (SEC-26).

    Abre a própria transação, curta: a chamada (até `LLM_READ_TIMEOUT`) fica fora dela.
    Erros sobem tipados, sem a chave (SEC-17).
    """
    with uow:
        # Ilegível fica `unreadable` no commit deste bloco; o erro sobe depois (ADR-0009).
        target = _generation_target(uow, cipher, user_id=user_id, snapshot=provider_snapshot)
    if target is None:
        raise NoActiveProvider("config_removed")
    if provider_snapshot.provider in KEY_PROVIDERS:
        if target.api_key is None:
            raise CredentialRejected("unreadable_key")
        register_secret(target.api_key)
    request = GenerationRequest(
        system_prompt=system_prompt,
        content=content,
        json_schema=json_schema,
        max_output_tokens=max_output_tokens,
    )
    return adapters[provider_snapshot.provider].generate(target, request)
