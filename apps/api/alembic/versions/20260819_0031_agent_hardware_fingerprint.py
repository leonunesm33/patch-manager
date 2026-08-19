"""add hardware fingerprint and identity conflict columns to machines

Servidores nascem de templates com hostname provisorio e sao renomeados
durante o provisionamento. Se o agente for instalado (enrollado) antes do
hostname final, o agent_id derivado do hostname pode colidir entre clones.
Estas colunas permitem detectar essa colisao via um fingerprint de hardware
enviado pelo agente a cada inventario, sem corrigir silenciosamente.

Revision ID: 20260819_0031
Revises: 20260714_0030
Create Date: 2026-08-19 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260819_0031"
down_revision = "20260714_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("machines", sa.Column("hardware_fingerprint", sa.String(255), nullable=True))
    op.add_column(
        "machines", sa.Column("identity_conflict_fingerprint", sa.String(255), nullable=True)
    )
    op.add_column(
        "machines",
        sa.Column("identity_conflict_detected_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("machines", "identity_conflict_detected_at")
    op.drop_column("machines", "identity_conflict_fingerprint")
    op.drop_column("machines", "hardware_fingerprint")
