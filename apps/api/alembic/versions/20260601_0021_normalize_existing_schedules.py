"""normalize existing schedules for structured scope

Revision ID: 20260601_0021
Revises: 20260601_0020
Create Date: 2026-06-01 15:20:00
"""

from alembic import op


revision = "20260601_0021"
down_revision = "20260601_0020"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE schedules
        SET
            scope = 'SO: Windows',
            scope_type = 'os',
            scope_value = 'Windows',
            cron_label = CASE
                WHEN recurrence = 'monthly' THEN 'Mensal, ' || install_time
                WHEN recurrence = 'weekly' THEN 'Semanal, ' || install_time
                WHEN recurrence = 'once' THEN 'Unica, ' || install_time
                ELSE 'Diaria, ' || install_time
            END
        WHERE lower(scope) LIKE '%windows%'
           OR lower(scope_value) LIKE '%windows%'
        """
    )
    op.execute(
        """
        UPDATE schedules
        SET
            scope = 'SO: Linux',
            scope_type = 'os',
            scope_value = 'Linux',
            cron_label = CASE
                WHEN recurrence = 'monthly' THEN 'Mensal, ' || install_time
                WHEN recurrence = 'daily' THEN 'Diaria, ' || install_time
                WHEN recurrence = 'once' THEN 'Unica, ' || install_time
                ELSE 'Semanal, ' || install_time
            END
        WHERE lower(scope) LIKE '%linux%'
           OR lower(scope) LIKE '%ubuntu%'
           OR lower(scope_value) LIKE '%linux%'
           OR lower(scope_value) LIKE '%ubuntu%'
        """
    )


def downgrade() -> None:
    pass
