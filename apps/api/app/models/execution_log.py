from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ExecutionLogModel(Base):
    __tablename__ = "execution_logs"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    schedule_id: Mapped[str] = mapped_column(String(80), index=True)
    schedule_name: Mapped[str] = mapped_column(String(120))
    machine_id: Mapped[str] = mapped_column(String(120), index=True)
    machine_name: Mapped[str] = mapped_column(String(120))
    patch_id: Mapped[str] = mapped_column(String(120), index=True)
    platform: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(30), index=True)
    result: Mapped[str] = mapped_column(String(30), index=True)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
