"""create daily and weekly missions tables

Revision ID: e8a1f4c2b9d0
Revises: dc18282faa13
Create Date: 2026-07-07 15:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8a1f4c2b9d0"
down_revision: str | Sequence[str] | None = "dc18282faa13"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "daily_missions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("mission_date", sa.Date(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "mission_date", name="uq_daily_missions_user_date"),
    )
    op.create_index(
        op.f("ix_daily_missions_mission_date"), "daily_missions", ["mission_date"], unique=False
    )
    op.create_index(op.f("ix_daily_missions_user_id"), "daily_missions", ["user_id"], unique=False)

    op.create_table(
        "weekly_missions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("iso_year", sa.Integer(), nullable=False),
        sa.Column("iso_week", sa.Integer(), nullable=False),
        sa.Column("module_id", sa.UUID(), nullable=False),
        sa.Column("bonus_awarded", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["module_id"], ["modules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "iso_year", "iso_week", name="uq_weekly_missions_user_year_week"
        ),
    )
    op.create_index(
        op.f("ix_weekly_missions_module_id"), "weekly_missions", ["module_id"], unique=False
    )
    op.create_index(
        op.f("ix_weekly_missions_user_id"), "weekly_missions", ["user_id"], unique=False
    )

    op.create_table(
        "daily_mission_lessons",
        sa.Column("daily_mission_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["daily_mission_id"], ["daily_missions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "daily_mission_id", "lesson_id", name="uq_daily_mission_lessons_mission_lesson"
        ),
    )
    op.create_index(
        op.f("ix_daily_mission_lessons_daily_mission_id"),
        "daily_mission_lessons",
        ["daily_mission_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_daily_mission_lessons_lesson_id"),
        "daily_mission_lessons",
        ["lesson_id"],
        unique=False,
    )

    op.create_table(
        "weekly_mission_lessons",
        sa.Column("weekly_mission_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["weekly_mission_id"], ["weekly_missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "weekly_mission_id", "lesson_id", name="uq_weekly_mission_lessons_mission_lesson"
        ),
    )
    op.create_index(
        op.f("ix_weekly_mission_lessons_lesson_id"),
        "weekly_mission_lessons",
        ["lesson_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_weekly_mission_lessons_weekly_mission_id"),
        "weekly_mission_lessons",
        ["weekly_mission_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_weekly_mission_lessons_weekly_mission_id"), table_name="weekly_mission_lessons"
    )
    op.drop_index(op.f("ix_weekly_mission_lessons_lesson_id"), table_name="weekly_mission_lessons")
    op.drop_table("weekly_mission_lessons")
    op.drop_index(op.f("ix_daily_mission_lessons_lesson_id"), table_name="daily_mission_lessons")
    op.drop_index(
        op.f("ix_daily_mission_lessons_daily_mission_id"), table_name="daily_mission_lessons"
    )
    op.drop_table("daily_mission_lessons")
    op.drop_index(op.f("ix_weekly_missions_user_id"), table_name="weekly_missions")
    op.drop_index(op.f("ix_weekly_missions_module_id"), table_name="weekly_missions")
    op.drop_table("weekly_missions")
    op.drop_index(op.f("ix_daily_missions_user_id"), table_name="daily_missions")
    op.drop_index(op.f("ix_daily_missions_mission_date"), table_name="daily_missions")
    op.drop_table("daily_missions")
