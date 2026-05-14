"""add user profile fields

Revision ID: 20260513_0018
Revises: 20260428_0017
Create Date: 2026-05-13 20:40:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260513_0018"
down_revision = "20260428_0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_initials", sa.String(length=4), nullable=True))
    op.add_column("users", sa.Column("avatar_color", sa.String(length=32), nullable=True))
    op.execute("UPDATE users SET role = 'user' WHERE role IN ('operator', 'viewer')")
    op.execute("UPDATE users SET role = 'admin' WHERE role IS NULL OR role = ''")


def downgrade() -> None:
    op.drop_column("users", "avatar_color")
    op.drop_column("users", "avatar_initials")
