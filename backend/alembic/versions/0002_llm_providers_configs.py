"""llm_providers: llm_configs

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "llm_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("base_url", sa.String(), nullable=True),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("context_window", sa.Integer(), nullable=False),
        sa.Column("key_ciphertext", sa.LargeBinary(), nullable=True),
        sa.Column("key_nonce", sa.LargeBinary(), nullable=True),
        sa.Column("key_version", sa.Integer(), nullable=True),
        sa.Column("key_mask", sa.String(), nullable=True),
        sa.Column("key_status", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id", "provider", name="uq_llm_configs_user_provider"),
        sa.CheckConstraint(
            "provider IN ('openai', 'anthropic', 'deepseek', 'ollama')",
            name="ck_llm_configs_provider",
        ),
        sa.CheckConstraint("context_window > 0", name="ck_llm_configs_context_window"),
        sa.CheckConstraint("key_status IN ('ok', 'unreadable')", name="ck_llm_configs_key_status"),
        sa.CheckConstraint("is_active IN (0, 1)", name="ck_llm_configs_is_active"),
    )
    op.create_index(
        "uq_llm_configs_one_active",
        "llm_configs",
        ["user_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
    )


def downgrade() -> None:
    op.drop_index("uq_llm_configs_one_active", table_name="llm_configs")
    op.drop_table("llm_configs")
