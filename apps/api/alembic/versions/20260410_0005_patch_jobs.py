"""add patch jobs

Revision ID: 20260410_0005
Revises: 20260410_0004
Create Date: 2026-04-10 00:20:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0005"
down_revision = "20260410_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "patch_jobs",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("schedule_id", sa.String(length=80), nullable=False),
        sa.Column("schedule_name", sa.String(length=120), nullable=False),
        sa.Column("machine_id", sa.String(length=120), nullable=False),
        sa.Column("machine_name", sa.String(length=120), nullable=False),
        sa.Column("patch_id", sa.String(length=120), nullable=False),
        sa.Column("platform", sa.String(length=50), nullable=False),
        sa.Column("severity", sa.String(length=30), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_patch_jobs_machine_id", "patch_jobs", ["machine_id"], unique=False)
    op.create_index("ix_patch_jobs_patch_id", "patch_jobs", ["patch_id"], unique=False)
    op.create_index("ix_patch_jobs_schedule_id", "patch_jobs", ["schedule_id"], unique=False)
    op.create_index("ix_patch_jobs_severity", "patch_jobs", ["severity"], unique=False)
    op.create_index("ix_patch_jobs_status", "patch_jobs", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_patch_jobs_status", table_name="patch_jobs")
    op.drop_index("ix_patch_jobs_severity", table_name="patch_jobs")
    op.drop_index("ix_patch_jobs_schedule_id", table_name="patch_jobs")
    op.drop_index("ix_patch_jobs_patch_id", table_name="patch_jobs")
    op.drop_index("ix_patch_jobs_machine_id", table_name="patch_jobs")
    op.drop_table("patch_jobs")
