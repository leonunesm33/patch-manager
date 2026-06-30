"""fix windows_command_timeout_seconds from 60 to 7200 for existing installations

Migration 0026 changed the code default from 60s to 1800s but did not update
the DB value on installations that already had 60 stored.  7200s (2 hours) is
more appropriate: cumulative updates on a freshly provisioned Windows Server
can be several GBs — downloads alone can take more than 30 minutes.

Revision ID: 20260630_0029
Revises: 20260630_0028
Create Date: 2026-06-30 00:00:00
"""

from alembic import op
from sqlalchemy.orm import Session
from sqlalchemy import text


revision = "20260630_0029"
down_revision = "20260630_0028"
branch_labels = None
depends_on = None

_KEY = "windows_command_timeout_seconds"
_OLD_VALUE = "60"
_NEW_VALUE = "7200"


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    row = session.execute(
        text("SELECT value FROM system_settings WHERE key = :key"),
        {"key": _KEY},
    ).fetchone()
    if row is not None and row[0] == _OLD_VALUE:
        session.execute(
            text("UPDATE system_settings SET value = :new WHERE key = :key"),
            {"new": _NEW_VALUE, "key": _KEY},
        )
        session.commit()


def downgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)
    row = session.execute(
        text("SELECT value FROM system_settings WHERE key = :key"),
        {"key": _KEY},
    ).fetchone()
    if row is not None and row[0] == _NEW_VALUE:
        session.execute(
            text("UPDATE system_settings SET value = :old WHERE key = :key"),
            {"old": _OLD_VALUE, "key": _KEY},
        )
        session.commit()
