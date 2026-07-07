"""add schools to learning catalog

Revision ID: f1b2c3d4e5f6
Revises: a4f2c8d92b31
Create Date: 2026-07-07 09:45:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "a4f2c8d92b31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SCHOOL_ID = "11111111-1111-4111-8111-111111111111"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "schools",
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("icon", sa.String(), nullable=True),
        sa.Column("order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("updated_by", sa.UUID(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_schools_slug"),
    )
    op.create_index(op.f("ix_schools_order"), "schools", ["order"], unique=False)

    op.execute(
        sa.text(
            """
            INSERT INTO schools (
                id, title, slug, description, icon, "order", is_active, version
            )
            VALUES (
                CAST(:id AS uuid),
                'Claude Academy',
                'claude-academy',
                'Escola principal com trilhas de IA, Claude e desenvolvimento assistido.',
                'graduation-cap',
                1,
                true,
                1
            )
            """
        ).bindparams(sa.bindparam("id", DEFAULT_SCHOOL_ID, type_=sa.String()))
    )

    op.add_column("tracks", sa.Column("school_id", sa.UUID(), nullable=True))
    op.execute(
        sa.text(
            f"UPDATE tracks SET school_id = '{DEFAULT_SCHOOL_ID}'::uuid "
            "WHERE school_id IS NULL"
        )
    )
    op.alter_column("tracks", "school_id", nullable=False)
    op.create_foreign_key(
        "fk_tracks_school_id_schools",
        "tracks",
        "schools",
        ["school_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_tracks_school_id"), "tracks", ["school_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_tracks_school_id"), table_name="tracks")
    op.drop_constraint("fk_tracks_school_id_schools", "tracks", type_="foreignkey")
    op.drop_column("tracks", "school_id")
    op.drop_index(op.f("ix_schools_order"), table_name="schools")
    op.drop_table("schools")
