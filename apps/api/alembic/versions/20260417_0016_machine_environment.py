"""add machine environment

Revision ID: 20260417_0016
Revises: 20260417_0015
Create Date: 2026-04-17 18:30:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_0016"
down_revision = "20260417_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "machines",
        sa.Column("environment", sa.String(length=32), nullable=False, server_default="production"),
    )
    op.alter_column("machines", "environment", server_default=None)


def downgrade() -> None:
    op.drop_column("machines", "environment")
