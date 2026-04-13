"""add system settings

Revision ID: 20260410_0007
Revises: 20260410_0006
Create Date: 2026-04-10 00:40:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0007"
down_revision = "20260410_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("value", sa.String(length=255), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("key"),
    )
    op.execute(
        "INSERT INTO system_settings (key, value) VALUES ('linux_agent_mode', 'dry-run')"
    )


def downgrade() -> None:
    op.drop_table("system_settings")
