from datetime import date, datetime

from sqlalchemy import Date, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    scope: Mapped[str] = mapped_column(String(120), index=True)
    scope_type: Mapped[str] = mapped_column(String(30), default="group", nullable=False, index=True)
    scope_value: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)
    cron_label: Mapped[str] = mapped_column(String(80))
    install_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    install_time: Mapped[str] = mapped_column(String(5), default="02:00", nullable=False)
    reboot_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reboot_time: Mapped[str | None] = mapped_column(String(5), nullable=True)
    recurrence: Mapped[str] = mapped_column(String(20), default="weekly", nullable=False)
    reboot_policy: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
