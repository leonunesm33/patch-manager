"""add agent inventory items

Revision ID: 20260417_0013
Revises: 20260417_0012
Create Date: 2026-04-17 19:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260417_0013"
down_revision: str | None = "20260417_0012"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_inventory_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("agent_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("identifier", sa.String(length=200), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("current_version", sa.String(length=120), nullable=True),
        sa.Column("target_version", sa.String(length=120), nullable=True),
        sa.Column("source", sa.String(length=200), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("kb_id", sa.String(length=80), nullable=True),
        sa.Column("security_only", sa.Boolean(), nullable=False),
        sa.Column("installed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_agent_inventory_items_agent_id"),
        "agent_inventory_items",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_inventory_items_item_type"),
        "agent_inventory_items",
        ["item_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_inventory_items_platform"),
        "agent_inventory_items",
        ["platform"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_inventory_items_platform"), table_name="agent_inventory_items")
    op.drop_index(op.f("ix_agent_inventory_items_item_type"), table_name="agent_inventory_items")
    op.drop_index(op.f("ix_agent_inventory_items_agent_id"), table_name="agent_inventory_items")
    op.drop_table("agent_inventory_items")
