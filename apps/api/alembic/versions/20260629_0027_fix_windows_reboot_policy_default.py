"""fix windows_reboot_policy default to manual (prevents unintended reboots)

Revision ID: 20260629_0027
Revises: 20260625_0026
Create Date: 2026-06-29 00:00:00
"""

from alembic import op


revision = "20260629_0027"
down_revision = "20260625_0026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Se o operador configurou explicitamente "maintenance-window" como policy global
    # de reboot Windows, isso causava reboots imediatos em TODAS as maquinas apos install,
    # ignorando a politica individual do agendamento (ex.: "Nao reiniciar").
    # O comportamento correto eh: reboots Windows sao gerenciados pelo scheduler via
    # scheduled_reboot command. O default global deve ser "manual".
    # Esta migration NAO sobrescreve se o valor ja for "manual" ou "notify" —
    # apenas corrige "maintenance-window" para "manual".
    op.execute(
        "UPDATE system_settings SET value = 'manual' "
        "WHERE key = 'windows_reboot_policy' AND value = 'maintenance-window'"
    )


def downgrade() -> None:
    op.execute(
        "UPDATE system_settings SET value = 'maintenance-window' "
        "WHERE key = 'windows_reboot_policy' AND value = 'manual'"
    )
