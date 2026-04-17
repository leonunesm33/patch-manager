"""expand system_settings value column

Revision ID: 20260417_0012
Revises: 20260413_0011
Create Date: 2026-04-17 15:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260417_0012"
down_revision = "20260413_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "system_settings",
        "value",
        existing_type=sa.String(length=255),
        type_=sa.Text(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "system_settings",
        "value",
        existing_type=sa.Text(),
        type_=sa.String(length=255),
        existing_nullable=False,
    )
