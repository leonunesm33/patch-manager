"""initial schema

Revision ID: 20260409_0001
Revises:
Create Date: 2026-04-09 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260409_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "machines",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("ip", sa.String(length=45), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("group_name", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("pending_patches", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_check_in", sa.DateTime(timezone=True), nullable=False),
        sa.Column("risk", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_machines_group_name", "machines", ["group_name"], unique=False)
    op.create_index("ix_machines_name", "machines", ["name"], unique=False)

    op.create_table(
        "patches",
        sa.Column("id", sa.String(length=120), nullable=False),
        sa.Column("target", sa.String(length=120), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("machines", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("release_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patches_severity", "patches", ["severity"], unique=False)
    op.create_index("ix_patches_target", "patches", ["target"], unique=False)

    op.create_table(
        "schedules",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("cron_label", sa.String(length=80), nullable=False),
        sa.Column("reboot_policy", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_schedules_name", "schedules", ["name"], unique=False)
    op.create_index("ix_schedules_scope", "schedules", ["scope"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_schedules_scope", table_name="schedules")
    op.drop_index("ix_schedules_name", table_name="schedules")
    op.drop_table("schedules")

    op.drop_index("ix_patches_target", table_name="patches")
    op.drop_index("ix_patches_severity", table_name="patches")
    op.drop_table("patches")

    op.drop_index("ix_machines_name", table_name="machines")
    op.drop_index("ix_machines_group_name", table_name="machines")
    op.drop_table("machines")
