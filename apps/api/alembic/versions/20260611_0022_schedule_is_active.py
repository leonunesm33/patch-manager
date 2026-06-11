"""add is_active to schedules

Revision ID: 20260611_0022
Revises: 20260601_0021
Create Date: 2026-06-11 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "20260611_0022"
down_revision = "20260601_0021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "schedules",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    op.drop_column("schedules", "is_active")
