from dataclasses import dataclass
from datetime import datetime

from snook.core.clock import to_iso
from snook.core.uow import UnitOfWork
from snook.modules.llm_providers import repository
from snook.modules.llm_providers.crypto import KeyCipher, MasterKeyMismatch, SealedKey
from snook.modules.llm_providers.models import (
    KEY_STATUS_OK,
    KEY_STATUS_UNREADABLE,
    LlmConfig,
)

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
) -> None:
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
