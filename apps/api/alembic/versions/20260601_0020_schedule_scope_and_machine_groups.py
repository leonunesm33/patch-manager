"""add structured schedule scope and machine groups

Revision ID: 20260601_0020
Revises: 20260601_0019
Create Date: 2026-06-01 14:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260601_0020"
down_revision = "20260601_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "machine_groups",
        sa.Column("id", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index(op.f("ix_machine_groups_name"), "machine_groups", ["name"], unique=False)

    op.add_column("schedules", sa.Column("scope_type", sa.String(length=30), nullable=False, server_default="group"))
    op.add_column("schedules", sa.Column("scope_value", sa.String(length=120), nullable=False, server_default=""))
    op.add_column("schedules", sa.Column("install_date", sa.Date(), nullable=True))
    op.add_column("schedules", sa.Column("install_time", sa.String(length=5), nullable=False, server_default="02:00"))
    op.add_column("schedules", sa.Column("reboot_date", sa.Date(), nullable=True))
    op.add_column("schedules", sa.Column("reboot_time", sa.String(length=5), nullable=True))
    op.add_column("schedules", sa.Column("recurrence", sa.String(length=20), nullable=False, server_default="weekly"))
    op.create_index(op.f("ix_schedules_scope_type"), "schedules", ["scope_type"], unique=False)
    op.create_index(op.f("ix_schedules_scope_value"), "schedules", ["scope_value"], unique=False)

    op.execute("UPDATE schedules SET scope_value = scope WHERE scope_value = ''")
    op.execute(
        """
        INSERT INTO machine_groups (id, name, description)
        SELECT
            'group-' || lower(regexp_replace(group_name, '[^a-zA-Z0-9]+', '-', 'g')),
            group_name,
            'Grupo criado a partir do inventario existente.'
        FROM (SELECT DISTINCT group_name FROM machines WHERE group_name IS NOT NULL AND group_name <> '') AS groups
        ON CONFLICT (name) DO NOTHING
        """
    )

    op.alter_column("schedules", "scope_type", server_default=None)
    op.alter_column("schedules", "scope_value", server_default=None)
    op.alter_column("schedules", "install_time", server_default=None)
    op.alter_column("schedules", "recurrence", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_schedules_scope_value"), table_name="schedules")
    op.drop_index(op.f("ix_schedules_scope_type"), table_name="schedules")
    op.drop_column("schedules", "recurrence")
    op.drop_column("schedules", "reboot_time")
    op.drop_column("schedules", "reboot_date")
    op.drop_column("schedules", "install_time")
    op.drop_column("schedules", "install_date")
    op.drop_column("schedules", "scope_value")
    op.drop_column("schedules", "scope_type")
    op.drop_index(op.f("ix_machine_groups_name"), table_name="machine_groups")
    op.drop_table("machine_groups")
