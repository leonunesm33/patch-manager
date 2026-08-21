"""add pending_security_critical_patches column to machines

Conta, dentre os patches pendentes/aprovados de uma maquina, quantos
sao de categoria "security" OU severidade "critical" — o mesmo criterio
do guardrail "Seguranca e criticos" do agente Linux. Exibido na coluna
"Patches pendentes" da tela de Maquinas como "total/segurança-críticos".

Revision ID: 20260821_0034
Revises: 20260820_0033
Create Date: 2026-08-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0034"
down_revision = "20260820_0033"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "machines",
        sa.Column(
            "pending_security_critical_patches",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("machines", "pending_security_critical_patches")
