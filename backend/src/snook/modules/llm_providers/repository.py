from sqlalchemy import select
from sqlalchemy.orm import Session

from snook.modules.llm_providers.models import LlmConfig


def get_config(session: Session, user_id: str, provider: str) -> LlmConfig | None:
    return session.scalar(
        select(LlmConfig).where(LlmConfig.user_id == user_id, LlmConfig.provider == provider)
    )


def add_config(session: Session, config: LlmConfig) -> None:
    session.add(config)
    session.flush()


def list_configs_with_key(session: Session) -> list[LlmConfig]:
    """Todas as linhas com chave cifrada, de todos os Usuários (rotação)."""
    return list(
        session.scalars(
            select(LlmConfig).where(LlmConfig.key_ciphertext.is_not(None)).order_by(LlmConfig.id)
        )
    )


def list_user_configs(session: Session, user_id: str) -> list[LlmConfig]:
    return list(session.scalars(select(LlmConfig).where(LlmConfig.user_id == user_id)))


def get_active_config(session: Session, user_id: str) -> LlmConfig | None:
    return session.scalar(
        select(LlmConfig).where(LlmConfig.user_id == user_id, LlmConfig.is_active.is_(True))
    )


def delete_config(session: Session, config: LlmConfig) -> None:
    session.delete(config)
    session.flush()
