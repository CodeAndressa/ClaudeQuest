"""create user_lesson_progress table

Revision ID: a4f2c8d92b31
Revises: b8f0ad4e3588
Create Date: 2026-07-06 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a4f2c8d92b31"
down_revision: Union[str, Sequence[str], None] = "b8f0ad4e3588"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "user_lesson_progress",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("lesson_id", sa.UUID(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("xp_awarded", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["lesson_id"], ["lessons.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "lesson_id", name="uq_user_lesson_progress_user_lesson"),
    )
    op.create_index(op.f("ix_user_lesson_progress_lesson_id"), "user_lesson_progress", ["lesson_id"], unique=False)
    op.create_index(op.f("ix_user_lesson_progress_user_id"), "user_lesson_progress", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_user_lesson_progress_user_id"), table_name="user_lesson_progress")
    op.drop_index(op.f("ix_user_lesson_progress_lesson_id"), table_name="user_lesson_progress")
    op.drop_table("user_lesson_progress")
