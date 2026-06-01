"""add patch display name

Revision ID: 20260601_0019
Revises: 20260513_0018
Create Date: 2026-06-01 13:20:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0019"
down_revision = "20260513_0018"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("patches", sa.Column("display_name", sa.String(length=500), nullable=True))
    op.execute("UPDATE patches SET display_name = id WHERE display_name IS NULL")


def downgrade() -> None:
    op.drop_column("patches", "display_name")
