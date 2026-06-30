"""expand post_patch_message column from 1000 to 4000 chars

Windows WUA error output includes one WUA_UPDATE line per pending patch.
On a fresh installation with many pending updates the combined string easily
exceeds 1000 chars, causing a DataError on submit_job_result and a 500.

Revision ID: 20260630_0028
Revises: 20260629_0027
Create Date: 2026-06-30 00:00:00
"""

import sqlalchemy as sa
from alembic import op


revision = "20260630_0028"
down_revision = "20260629_0027"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "agent_inventory_snapshots",
        "post_patch_message",
        existing_type=sa.String(1000),
        type_=sa.String(4000),
        existing_nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "agent_inventory_snapshots",
        "post_patch_message",
        existing_type=sa.String(4000),
        type_=sa.String(1000),
        existing_nullable=True,
    )
