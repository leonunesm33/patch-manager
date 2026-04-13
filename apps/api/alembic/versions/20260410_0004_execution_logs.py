"""add execution logs

Revision ID: 20260410_0004
Revises: 20260410_0003
Create Date: 2026-04-10 00:10:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0004"
down_revision = "20260410_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "execution_logs",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("schedule_id", sa.String(length=80), nullable=False),
        sa.Column("schedule_name", sa.String(length=120), nullable=False),
        sa.Column("machine_id", sa.String(length=120), nullable=False),
        sa.Column("machine_name", sa.String(length=120), nullable=False),
        sa.Column("patch_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("result", sa.String(length=30), nullable=False),
        sa.Column("duration_seconds", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("executed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_execution_logs_machine_id", "execution_logs", ["machine_id"], unique=False)
    op.create_index("ix_execution_logs_patch_id", "execution_logs", ["patch_id"], unique=False)
    op.create_index("ix_execution_logs_result", "execution_logs", ["result"], unique=False)
    op.create_index("ix_execution_logs_schedule_id", "execution_logs", ["schedule_id"], unique=False)
    op.create_index("ix_execution_logs_severity", "execution_logs", ["severity"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_execution_logs_severity", table_name="execution_logs")
    op.drop_index("ix_execution_logs_schedule_id", table_name="execution_logs")
    op.drop_index("ix_execution_logs_result", table_name="execution_logs")
    op.drop_index("ix_execution_logs_patch_id", table_name="execution_logs")
    op.drop_index("ix_execution_logs_machine_id", table_name="execution_logs")
    op.drop_table("execution_logs")
