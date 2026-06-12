"""add category and severity to agent_inventory_items

Revision ID: 20260612_0024
Revises: 20260611_0023
Create Date: 2026-06-12 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "20260612_0024"
down_revision = "20260611_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_inventory_items", sa.Column("category", sa.String(50), nullable=True))
    op.add_column("agent_inventory_items", sa.Column("severity", sa.String(50), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_inventory_items", "severity")
    op.drop_column("agent_inventory_items", "category")
