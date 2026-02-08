"""add ground sources

Revision ID: 20260207_0002
Revises: 20260205_0001
Create Date: 2026-02-07 00:02:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260207_0002"
down_revision = "20260205_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ground_sources",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=255), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("canonical_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ground_sources_user_id", "ground_sources", ["user_id"], unique=False)
    op.create_index("ix_ground_sources_content_hash", "ground_sources", ["content_hash"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ground_sources_content_hash", table_name="ground_sources")
    op.drop_index("ix_ground_sources_user_id", table_name="ground_sources")
    op.drop_table("ground_sources")
