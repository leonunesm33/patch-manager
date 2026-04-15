"""add agent credentials

Revision ID: 20260413_0008
Revises: 20260410_0007
Create Date: 2026-04-13 10:00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

revision = "20260413_0008"
down_revision = "20260410_0007"
branch_labels = None
depends_on = None

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def upgrade() -> None:
    op.create_table(
        "agent_credentials",
        sa.Column("agent_id", sa.String(length=80), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=False),
        sa.Column("description", sa.String(length=160), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("agent_id"),
    )
    op.create_index(op.f("ix_agent_credentials_platform"), "agent_credentials", ["platform"], unique=False)

    credentials_table = sa.table(
        "agent_credentials",
        sa.column("agent_id", sa.String),
        sa.column("platform", sa.String),
        sa.column("description", sa.String),
        sa.column("key_hash", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(
        credentials_table,
        [
            {
                "agent_id": "linux-agent-01",
                "platform": "linux",
                "description": "Linux agent default credential",
                "key_hash": pwd_context.hash("patch-manager-agent-key"),
                "is_active": True,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_credentials_platform"), table_name="agent_credentials")
    op.drop_table("agent_credentials")
