"""add os_release column to machines

A coluna PLATAFORMA ja informa o sistema (Windows/Linux) mas nao a versao
amigavel do SO (ex.: "Server 2022", "Ubuntu 24.04"). Esta coluna guarda essa
versao, coletada pelo agente a cada inventario, para substituir a coluna
AMBIENTE (nao utilizada) na tela de Maquinas.

Revision ID: 20260820_0032
Revises: 20260819_0031
Create Date: 2026-08-20 00:00:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_0032"
down_revision = "20260819_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("machines", sa.Column("os_release", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("machines", "os_release")
