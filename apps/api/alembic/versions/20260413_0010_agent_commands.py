"""add agent commands

Revision ID: 20260413_0010
Revises: 20260413_0009
Create Date: 2026-04-13 15:40:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260413_0010"
down_revision: str | None = "20260413_0009"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_commands",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("agent_id", sa.String(length=120), nullable=False),
        sa.Column("command_type", sa.String(length=60), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requested_by", sa.String(length=120), nullable=False),
        sa.Column("message", sa.String(length=255), nullable=True),
        sa.Column("payload_json", sa.String(length=1000), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_agent_commands_agent_id"), "agent_commands", ["agent_id"], unique=False)
    op.create_index(op.f("ix_agent_commands_command_type"), "agent_commands", ["command_type"], unique=False)
    op.create_index(op.f("ix_agent_commands_requested_by"), "agent_commands", ["requested_by"], unique=False)
    op.create_index(op.f("ix_agent_commands_status"), "agent_commands", ["status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_agent_commands_status"), table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_requested_by"), table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_command_type"), table_name="agent_commands")
    op.drop_index(op.f("ix_agent_commands_agent_id"), table_name="agent_commands")
    op.drop_table("agent_commands")
