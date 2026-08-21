from datetime import datetime

from sqlalchemy import DateTime, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentIdentityHistoryModel(Base):
    __tablename__ = "agent_identity_history"
    __table_args__ = (
        UniqueConstraint(
            "command_id",
            "event_type",
            name="uq_agent_identity_history_command_event",
        ),
    )

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    agent_id: Mapped[str] = mapped_column(String(120), index=True)
    new_agent_id: Mapped[str | None] = mapped_column(String(120), index=True, nullable=True)
    command_id: Mapped[str | None] = mapped_column(String(80), index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True)
    platform: Mapped[str | None] = mapped_column(String(30), nullable=True)
    hostname: Mapped[str | None] = mapped_column(String(120), nullable=True)
    hardware_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    previous_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    actor: Mapped[str] = mapped_column(String(120))
    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
