from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduleModel(Base):
    __tablename__ = "schedules"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    scope: Mapped[str] = mapped_column(String(120), index=True)
    cron_label: Mapped[str] = mapped_column(String(80))
    reboot_policy: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
