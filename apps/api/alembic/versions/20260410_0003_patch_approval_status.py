"""add patch approval status

Revision ID: 20260410_0003
Revises: 20260409_0002
Create Date: 2026-04-10 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0003"
down_revision = "20260409_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "patches",
        sa.Column("approval_status", sa.String(length=30), nullable=False, server_default="pending"),
    )
    op.add_column("patches", sa.Column("reviewed_by", sa.String(length=80), nullable=True))
    op.add_column("patches", sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_patches_approval_status", "patches", ["approval_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patches_approval_status", table_name="patches")
    op.drop_column("patches", "reviewed_at")
    op.drop_column("patches", "reviewed_by")
    op.drop_column("patches", "approval_status")
