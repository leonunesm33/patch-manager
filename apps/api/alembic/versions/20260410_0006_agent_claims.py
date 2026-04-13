"""add agent claim fields to patch jobs

Revision ID: 20260410_0006
Revises: 20260410_0005
Create Date: 2026-04-10 00:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0006"
down_revision = "20260410_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patch_jobs", sa.Column("claimed_by_agent", sa.String(length=120), nullable=True))
    op.add_column("patch_jobs", sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("patch_jobs", "claimed_at")
    op.drop_column("patch_jobs", "claimed_by_agent")
