"""add patch category

Revision ID: 20260428_0017
Revises: 20260417_0016
Create Date: 2026-04-28 22:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260428_0017"
down_revision: str | None = "20260417_0016"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "patches",
        sa.Column("category", sa.String(length=40), nullable=False, server_default="security"),
    )
    op.create_index(op.f("ix_patches_category"), "patches", ["category"], unique=False)
    op.alter_column("patches", "category", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_patches_category"), table_name="patches")
    op.drop_column("patches", "category")
