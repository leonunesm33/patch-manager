from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentEnrollmentModel(Base):
    __tablename__ = "agent_enrollments"

    agent_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    platform: Mapped[str] = mapped_column(String(30), index=True)
    hostname: Mapped[str] = mapped_column(String(120), index=True)
    primary_ip: Mapped[str] = mapped_column(String(45))
    os_name: Mapped[str] = mapped_column(String(60))
    os_version: Mapped[str] = mapped_column(String(120))
    kernel_version: Mapped[str] = mapped_column(String(120))
    agent_version: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(30), index=True, default="pending")
    issued_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
