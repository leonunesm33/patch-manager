"""add agent enrollments

Revision ID: 20260413_0009
Revises: 20260413_0008
Create Date: 2026-04-13 14:00:00
"""

import sqlalchemy as sa
from alembic import op

revision = "20260413_0009"
down_revision = "20260413_0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_enrollments",
        sa.Column("agent_id", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("hostname", sa.String(length=120), nullable=False),
        sa.Column("primary_ip", sa.String(length=45), nullable=False),
        sa.Column("os_name", sa.String(length=60), nullable=False),
        sa.Column("os_version", sa.String(length=120), nullable=False),
        sa.Column("kernel_version", sa.String(length=120), nullable=False),
        sa.Column("agent_version", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("issued_key", sa.String(length=255), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index(op.f("ix_agent_enrollments_platform"), "agent_enrollments", ["platform"], unique=False)
    op.create_index(op.f("ix_agent_enrollments_hostname"), "agent_enrollments", ["hostname"], unique=False)
    op.create_index(op.f("ix_agent_enrollments_status"), "agent_enrollments", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_enrollments_status"), table_name="agent_enrollments")
    op.drop_index(op.f("ix_agent_enrollments_hostname"), table_name="agent_enrollments")
    op.drop_index(op.f("ix_agent_enrollments_platform"), table_name="agent_enrollments")
    op.drop_table("agent_enrollments")
