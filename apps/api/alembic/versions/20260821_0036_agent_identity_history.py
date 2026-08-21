"""add agent identity history and protect active reidentification commands

Revision ID: 20260821_0036
Revises: 20260821_0035
Create Date: 2026-08-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0036"
down_revision = "20260821_0035"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agent_identity_history",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("agent_id", sa.String(length=120), nullable=False),
        sa.Column("new_agent_id", sa.String(length=120), nullable=True),
        sa.Column("command_id", sa.String(length=80), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("platform", sa.String(length=30), nullable=True),
        sa.Column("hostname", sa.String(length=120), nullable=True),
        sa.Column("hardware_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("previous_fingerprint", sa.String(length=255), nullable=True),
        sa.Column("actor", sa.String(length=120), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=True),
        sa.Column("message", sa.String(length=1000), nullable=True),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "command_id",
            "event_type",
            name="uq_agent_identity_history_command_event",
        ),
    )
    op.create_index(
        op.f("ix_agent_identity_history_agent_id"),
        "agent_identity_history",
        ["agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identity_history_new_agent_id"),
        "agent_identity_history",
        ["new_agent_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identity_history_command_id"),
        "agent_identity_history",
        ["command_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identity_history_event_type"),
        "agent_identity_history",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_agent_identity_history_status"),
        "agent_identity_history",
        ["status"],
        unique=False,
    )
    op.create_index(
        "uq_agent_commands_active_force_reidentify",
        "agent_commands",
        ["agent_id"],
        unique=True,
        postgresql_where=sa.text(
            "command_type = 'force_reidentify' AND status IN ('pending', 'running')"
        ),
        sqlite_where=sa.text(
            "command_type = 'force_reidentify' AND status IN ('pending', 'running')"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_agent_commands_active_force_reidentify",
        table_name="agent_commands",
    )
    op.drop_index(
        op.f("ix_agent_identity_history_status"),
        table_name="agent_identity_history",
    )
    op.drop_index(
        op.f("ix_agent_identity_history_event_type"),
        table_name="agent_identity_history",
    )
    op.drop_index(
        op.f("ix_agent_identity_history_command_id"),
        table_name="agent_identity_history",
    )
    op.drop_index(
        op.f("ix_agent_identity_history_new_agent_id"),
        table_name="agent_identity_history",
    )
    op.drop_index(
        op.f("ix_agent_identity_history_agent_id"),
        table_name="agent_identity_history",
    )
    op.drop_table("agent_identity_history")
