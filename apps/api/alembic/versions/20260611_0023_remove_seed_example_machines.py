"""remove seed example machines

Revision ID: 20260611_0023
Revises: 20260611_0022
Create Date: 2026-06-11 00:00:00
"""

from alembic import op


revision = "20260611_0023"
down_revision = "20260611_0022"
branch_labels = None
depends_on = None

_EXAMPLE_IDS = ("srv-web-01", "srv-db-02", "ubuntu-prod-03")


def upgrade() -> None:
    for machine_id in _EXAMPLE_IDS:
        op.execute(f"DELETE FROM machines WHERE id = '{machine_id}'")


def downgrade() -> None:
    pass
