from sqlalchemy import CheckConstraint, ForeignKey, Index, LargeBinary, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from snook.core.db import Base

PROVIDERS = ("openai", "anthropic", "deepseek", "ollama")
KEY_STATUS_OK = "ok"
KEY_STATUS_UNREADABLE = "unreadable"


class LlmConfig(Base):
    """Configuração de LLM do Usuário. Chave só cifrada (ADR-0009, SEC-07)."""

    __tablename__ = "llm_configs"
    __table_args__ = (
        UniqueConstraint("user_id", "provider", name="uq_llm_configs_user_provider"),
        CheckConstraint(
            "provider IN ('openai', 'anthropic', 'deepseek', 'ollama')",
            name="ck_llm_configs_provider",
        ),
        CheckConstraint("context_window > 0", name="ck_llm_configs_context_window"),
        CheckConstraint("key_status IN ('ok', 'unreadable')", name="ck_llm_configs_key_status"),
        CheckConstraint("is_active IN (0, 1)", name="ck_llm_configs_is_active"),
        Index(
            "uq_llm_configs_one_active",
            "user_id",
            unique=True,
            sqlite_where="is_active = 1",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    provider: Mapped[str] = mapped_column(String)
    base_url: Mapped[str | None] = mapped_column(String)
    model: Mapped[str] = mapped_column(String(200))
    context_window: Mapped[int]
    key_ciphertext: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_nonce: Mapped[bytes | None] = mapped_column(LargeBinary)
    key_version: Mapped[int | None]
    key_mask: Mapped[str | None] = mapped_column(String)
    key_status: Mapped[str] = mapped_column(String, default=KEY_STATUS_OK)
    is_active: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[str] = mapped_column(String)
    updated_at: Mapped[str] = mapped_column(String)
