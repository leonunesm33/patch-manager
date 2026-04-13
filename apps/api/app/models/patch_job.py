from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PatchJobModel(Base):
    __tablename__ = "patch_jobs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(80), index=True)
    schedule_name: Mapped[str] = mapped_column(String(120))
    machine_id: Mapped[str] = mapped_column(String(120), index=True)
    machine_name: Mapped[str] = mapped_column(String(120))
    patch_id: Mapped[str] = mapped_column(String(120), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(30), index=True)
    status: Mapped[str] = mapped_column(String(30), index=True, default="pending")
    claimed_by_agent: Mapped[str | None] = mapped_column(String(120), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
