"""expand patch_jobs.error_message from VARCHAR(255) to TEXT

Revision ID: 20260625_0025
Revises: 20260612_0024
Create Date: 2026-06-25 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "20260625_0025"
down_revision = "20260612_0024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "patch_jobs",
        "error_message",
        existing_type=sa.String(255),
        type_=sa.Text,
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "patch_jobs",
        "error_message",
        existing_type=sa.Text,
        type_=sa.String(255),
        existing_nullable=True,
    )
