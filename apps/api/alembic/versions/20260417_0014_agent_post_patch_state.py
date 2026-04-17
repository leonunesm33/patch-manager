"""add agent post patch state

Revision ID: 20260417_0014
Revises: 20260417_0013
Create Date: 2026-04-17 20:05:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260417_0014"
down_revision: str | None = "20260417_0013"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "agent_inventory_snapshots",
        sa.Column("post_patch_state", sa.String(length=40), nullable=False, server_default="idle"),
    )
    op.add_column(
        "agent_inventory_snapshots",
        sa.Column("post_patch_message", sa.String(length=1000), nullable=True),
    )
    op.add_column(
        "agent_inventory_snapshots",
        sa.Column("last_apply_result", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "agent_inventory_snapshots",
        sa.Column("last_apply_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "agent_inventory_snapshots",
        sa.Column("reboot_scheduled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("agent_inventory_snapshots", "reboot_scheduled_at")
    op.drop_column("agent_inventory_snapshots", "last_apply_at")
    op.drop_column("agent_inventory_snapshots", "last_apply_result")
    op.drop_column("agent_inventory_snapshots", "post_patch_message")
    op.drop_column("agent_inventory_snapshots", "post_patch_state")
