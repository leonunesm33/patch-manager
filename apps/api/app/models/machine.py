from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MachineModel(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    ip: Mapped[str] = mapped_column(String(45))
    platform: Mapped[str] = mapped_column(String(50))
    environment: Mapped[str] = mapped_column(String(32), default="production", nullable=False)
    os_release: Mapped[str | None] = mapped_column(String(80), nullable=True)
    group: Mapped[str] = mapped_column("group_name", String(120), index=True)
    status: Mapped[str] = mapped_column(String(30))
    pending_patches: Mapped[int] = mapped_column(Integer, default=0)
    pending_security_critical_patches: Mapped[int] = mapped_column(Integer, default=0)
    last_check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    risk: Mapped[str] = mapped_column(String(30))
    hardware_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_conflict_fingerprint: Mapped[str | None] = mapped_column(String(255), nullable=True)
    identity_conflict_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    identity_conflict_auto_resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    identity_conflict_previous_fingerprint: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    identity_conflict_oscillation_detected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
