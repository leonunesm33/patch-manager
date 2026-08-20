"""add recurrence_weekday and recurrence_ordinal columns to schedules

Suporta o novo tipo de recorrencia "monthly_weekday" (ex.: 3a
quinta-feira do mes, ultima sexta-feira do mes). recurrence_weekday usa
a convencao de date.weekday() (0=segunda...6=domingo);
recurrence_ordinal e 1-4 para posicao fixa ou -1 para "ultima
ocorrencia no mes".

Revision ID: 20260820_0033
Revises: 20260820_0032
Create Date: 2026-08-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0033"
down_revision = "20260820_0032"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("schedules", sa.Column("recurrence_weekday", sa.Integer(), nullable=True))
    op.add_column("schedules", sa.Column("recurrence_ordinal", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("schedules", "recurrence_ordinal")
    op.drop_column("schedules", "recurrence_weekday")
