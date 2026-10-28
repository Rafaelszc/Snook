"""participants: participants, speaker_links

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "participants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "meeting_id",
            sa.String(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_norm", sa.String(), nullable=False),
        sa.UniqueConstraint("meeting_id", "name_norm", name="uq_participants_meeting_name"),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 100", name="ck_participants_name"),
    )
    op.create_table(
        "speaker_links",
        sa.Column(
            "meeting_id",
            sa.String(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("speaker_label", sa.String(), primary_key=True),
        sa.Column(
            "participant_id",
            sa.Integer(),
            sa.ForeignKey("participants.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("speaker_links")
    op.drop_table("participants")
