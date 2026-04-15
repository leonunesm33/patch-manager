"""add agent inventory snapshots

Revision ID: 20260413_0011
Revises: 20260413_0010
Create Date: 2026-04-13 16:10:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260413_0011"
down_revision: str | None = "20260413_0010"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_inventory_snapshots",
        sa.Column("agent_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("hostname", sa.String(length=120), nullable=False),
        sa.Column("primary_ip", sa.String(length=80), nullable=False),
        sa.Column("package_manager", sa.String(length=80), nullable=False),
        sa.Column("installed_packages", sa.Integer(), nullable=False),
        sa.Column("upgradable_packages", sa.Integer(), nullable=False),
        sa.Column("reboot_required", sa.Boolean(), nullable=False),
        sa.Column("installed_update_count", sa.Integer(), nullable=True),
        sa.Column("pending_update_summary", sa.String(length=1000), nullable=True),
        sa.Column("windows_update_source", sa.String(length=120), nullable=True),
        sa.Column("os_name", sa.String(length=120), nullable=False),
        sa.Column("os_version", sa.String(length=120), nullable=False),
        sa.Column("kernel_version", sa.String(length=120), nullable=False),
        sa.Column("agent_version", sa.String(length=40), nullable=False),
        sa.Column("execution_mode", sa.String(length=40), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index(op.f("ix_agent_inventory_snapshots_hostname"), "agent_inventory_snapshots", ["hostname"], unique=False)
    op.create_index(op.f("ix_agent_inventory_snapshots_platform"), "agent_inventory_snapshots", ["platform"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_inventory_snapshots_platform"), table_name="agent_inventory_snapshots")
    op.drop_index(op.f("ix_agent_inventory_snapshots_hostname"), table_name="agent_inventory_snapshots")
    op.drop_table("agent_inventory_snapshots")
