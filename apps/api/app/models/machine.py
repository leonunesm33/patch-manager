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
    group: Mapped[str] = mapped_column("group_name", String(120), index=True)
    status: Mapped[str] = mapped_column(String(30))
    pending_patches: Mapped[int] = mapped_column(Integer, default=0)
    last_check_in: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    risk: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
