"""diarized_transcription: transcript_segments

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-23
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("speaker_label", sa.String(), nullable=False),
        sa.Column("start_seconds", sa.Float(), nullable=False),
        sa.Column("end_seconds", sa.Float(), nullable=False),
        sa.Column("text", sa.String(), nullable=False),
        sa.UniqueConstraint("meeting_id", "position", name="uq_transcript_segments_position"),
    )


def downgrade() -> None:
    op.drop_table("transcript_segments")
