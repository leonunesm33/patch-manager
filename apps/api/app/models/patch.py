from datetime import date, datetime

from sqlalchemy import Date, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PatchModel(Base):
    __tablename__ = "patches"

    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    target: Mapped[str] = mapped_column(String(120), index=True)
    severity: Mapped[str] = mapped_column(String(30), index=True)
    machines: Mapped[int] = mapped_column(Integer, default=0)
    release_date: Mapped[date] = mapped_column(Date)
    approval_status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(80), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
