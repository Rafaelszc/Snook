"""backlog_generation: epics, user_stories, acceptance_criteria, backlog_counters

Revision ID: 0007
Revises: 0006
Create Date: 2026-10-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def _meeting_id() -> sa.Column[str]:
    return sa.Column(
        "meeting_id",
        sa.String(),
        sa.ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "epics",
        sa.Column("id", sa.Integer(), primary_key=True),
        _meeting_id(),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("name_norm", sa.String(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("meeting_id", "name_norm", name="uq_epics_meeting_name"),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 200", name="ck_epics_name"),
    )
    op.create_table(
        "user_stories",
        sa.Column("id", sa.Integer(), primary_key=True),
        _meeting_id(),
        sa.Column(
            "epic_id",
            sa.Integer(),
            sa.ForeignKey("epics.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("us_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("as_a", sa.String(2000), nullable=False),
        sa.Column("i_want", sa.String(2000), nullable=False),
        sa.Column("so_that", sa.String(2000), nullable=False),
        sa.Column("priority", sa.String(), nullable=False),
        sa.Column("story_points", sa.Integer(), nullable=False),
        sa.Column(
            "requested_by",
            sa.Integer(),
            sa.ForeignKey("participants.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("requested_at_seconds", sa.Integer(), nullable=True),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.UniqueConstraint("meeting_id", "us_number", name="uq_user_stories_number"),
        sa.CheckConstraint("length(name) BETWEEN 1 AND 200", name="ck_user_stories_name"),
        sa.CheckConstraint(
            "length(as_a) BETWEEN 1 AND 2000 AND length(i_want) BETWEEN 1 AND 2000 "
            "AND length(so_that) BETWEEN 1 AND 2000",
            name="ck_user_stories_text",
        ),
        sa.CheckConstraint(
            "priority IN ('Low', 'Medium', 'High')", name="ck_user_stories_priority"
        ),
        sa.CheckConstraint(
            "story_points IN (1, 2, 3, 5, 8, 13)", name="ck_user_stories_story_points"
        ),
        sa.CheckConstraint(
            "requested_at_seconds IS NULL OR requested_at_seconds >= 0",
            name="ck_user_stories_requested_at",
        ),
    )
    op.create_table(
        "acceptance_criteria",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_story_id",
            sa.Integer(),
            sa.ForeignKey("user_stories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("given", sa.String(1000), nullable=False),
        sa.Column("when_", sa.String(1000), nullable=False),
        sa.Column("then_", sa.String(1000), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "length(given) BETWEEN 1 AND 1000 AND length(when_) BETWEEN 1 AND 1000 "
            "AND length(then_) BETWEEN 1 AND 1000",
            name="ck_acceptance_criteria_text",
        ),
    )
    op.create_table(
        "backlog_counters",
        sa.Column(
            "meeting_id",
            sa.String(),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("last_us_number", sa.Integer(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("backlog_counters")
    op.drop_table("acceptance_criteria")
    op.drop_table("user_stories")
    op.drop_table("epics")
