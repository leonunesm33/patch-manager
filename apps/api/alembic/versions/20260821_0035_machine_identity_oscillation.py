"""add identity oscillation tracking columns to machines

Suporte a auto-resolução de conflito de identidade com detecção de oscilação:
- identity_conflict_auto_resolved_at: quando foi a última auto-resolução
- identity_conflict_previous_fingerprint: fingerprint substituído na última
  auto-resolução (usado para detectar se o agente voltou ao valor anterior)
- identity_conflict_oscillation_detected_at: preenchido quando o mesmo
  agent_id alterna entre dois fingerprints dentro da janela de 1h — sinal de
  possível identidade duplicada (clone de template não re-enrolled)

Revision ID: 20260821_0035
Revises: 20260821_0034
Create Date: 2026-08-21 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260821_0035"
down_revision = "20260821_0034"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "machines",
        sa.Column("identity_conflict_auto_resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "machines",
        sa.Column("identity_conflict_previous_fingerprint", sa.String(255), nullable=True),
    )
    op.add_column(
        "machines",
        sa.Column(
            "identity_conflict_oscillation_detected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("machines", "identity_conflict_oscillation_detected_at")
    op.drop_column("machines", "identity_conflict_previous_fingerprint")
    op.drop_column("machines", "identity_conflict_auto_resolved_at")
