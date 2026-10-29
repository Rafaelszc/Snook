"""meetings: meetings

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column(
            "user_id",
            sa.String(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_ext", sa.String(), nullable=False),
        sa.Column("duration_seconds", sa.Float(), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("expected_speakers", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("failed_stage", sa.String(), nullable=True),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("split_reason", sa.String(), nullable=True),
        sa.Column("run_id", sa.String(), nullable=False),
        sa.Column("participants_confirmed_at", sa.String(), nullable=True),
        sa.Column("backlog_saved_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
        sa.CheckConstraint(
            "status IN ('pending', 'processing', 'transcribed', 'needs_split', "
            "'generating', 'done', 'failed')",
            name="ck_meetings_status",
        ),
        sa.CheckConstraint(
            "file_ext IN ('mp3', 'wav', 'm4a', 'ogg', 'webm', 'mp4')", name="ck_meetings_file_ext"
        ),
        sa.CheckConstraint(
            "failed_stage IS NULL OR failed_stage IN ('transcription', 'generation')",
            name="ck_meetings_failed_stage",
        ),
        sa.CheckConstraint(
            "status != 'failed' OR (failed_stage IS NOT NULL AND error_message IS NOT NULL)",
            name="ck_meetings_failed_fields",
        ),
        sa.CheckConstraint(
            "split_reason IS NULL OR split_reason IN ('too_long', 'adjust')",
            name="ck_meetings_split_reason",
        ),
        sa.CheckConstraint(
            "expected_speakers IS NULL OR expected_speakers BETWEEN 1 AND 20",
            name="ck_meetings_expected_speakers",
        ),
        sa.CheckConstraint(
            "duration_seconds > 0 AND duration_seconds <= 7200", name="ck_meetings_duration"
        ),
        sa.CheckConstraint("size_bytes <= 524288000", name="ck_meetings_size"),
        sa.CheckConstraint("length(title) BETWEEN 1 AND 200", name="ck_meetings_title"),
    )
    op.create_index("ix_meetings_user_created", "meetings", ["user_id", "created_at"])
    op.create_index("ix_meetings_status_created", "meetings", ["status", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_meetings_status_created", table_name="meetings")
    op.drop_index("ix_meetings_user_created", table_name="meetings")
    op.drop_table("meetings")
