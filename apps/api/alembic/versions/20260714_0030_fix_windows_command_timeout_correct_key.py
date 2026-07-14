"""fix windows_command_timeout using the correct settings key

Migration 0029 updated the key "windows_command_timeout_seconds" but the
settings service reads from "windows_command_timeout" (without _seconds).
The mismatch left the real key at its original value of "60" seconds, causing
every Windows agent to time out after one minute regardless of the job size.

This migration:
  1. Updates "windows_command_timeout" to 7200 when the stored value is < 300.
  2. Deletes the ghost key "windows_command_timeout_seconds" written by 0029.

Revision ID: 20260714_0030
Revises: 20260630_0029
Create Date: 2026-07-14 00:00:00
"""

from alembic import op
from sqlalchemy.orm import Session
from sqlalchemy import text


revision = "20260714_0030"
down_revision = "20260630_0029"
branch_labels = None
depends_on = None

_KEY = "windows_command_timeout"
_GHOST_KEY = "windows_command_timeout_seconds"
_NEW_VALUE = "7200"
_THRESHOLD = 300


def upgrade() -> None:
    bind = op.get_bind()
    session = Session(bind=bind)

    row = session.execute(
        text("SELECT value FROM system_settings WHERE key = :key"),
        {"key": _KEY},
    ).fetchone()

    if row is not None:
        try:
            current = int(row[0])
        except (TypeError, ValueError):
            current = 0
        if current < _THRESHOLD:
            session.execute(
                text("UPDATE system_settings SET value = :new WHERE key = :key"),
                {"new": _NEW_VALUE, "key": _KEY},
            )

    # Remove ghost key left by the broken migration 0029
    session.execute(
        text("DELETE FROM system_settings WHERE key = :key"),
        {"key": _GHOST_KEY},
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
            {"old": "60", "key": _KEY},
        )
        session.commit()
