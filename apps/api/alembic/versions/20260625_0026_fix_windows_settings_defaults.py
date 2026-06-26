"""fix windows apply settings defaults (scan_apply=true, download_install=true, timeout=1800)

Revision ID: 20260625_0026
Revises: 20260625_0025
Create Date: 2026-06-25 00:00:00
"""

from alembic import op


revision = "20260625_0026"
down_revision = "20260625_0025"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Corrige valores escritos pelo codigo antigo (defaults errados).
    # Nao sobrescreve valores que o usuario tiver alterado explicitamente para
    # algo diferente de "false" ou "60" — esses ja eram intencao do operador.
    op.execute(
        "UPDATE system_settings SET value = 'true' "
        "WHERE key = 'windows_scan_apply_enabled' AND value = 'false'"
    )
    op.execute(
        "UPDATE system_settings SET value = 'true' "
        "WHERE key = 'windows_download_install_enabled' AND value = 'false'"
    )
    op.execute(
        "UPDATE system_settings SET value = '1800' "
        "WHERE key = 'windows_command_timeout_seconds' AND value = '60'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET value = 'false' "
        "WHERE key = 'windows_scan_apply_enabled' AND value = 'true'"
    )
    op.execute(
        "UPDATE system_settings SET value = 'false' "
        "WHERE key = 'windows_download_install_enabled' AND value = 'true'"
    )
    op.execute(
        "UPDATE system_settings SET value = '60' "
        "WHERE key = 'windows_command_timeout_seconds' AND value = '1800'"
    )
