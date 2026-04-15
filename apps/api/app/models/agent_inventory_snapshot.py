from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentInventorySnapshotModel(Base):
    __tablename__ = "agent_inventory_snapshots"

    agent_id: Mapped[str] = mapped_column(String(120), primary_key=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    hostname: Mapped[str] = mapped_column(String(120), index=True)
    primary_ip: Mapped[str] = mapped_column(String(80))
    package_manager: Mapped[str] = mapped_column(String(80))
    installed_packages: Mapped[int] = mapped_column(Integer, default=0)
    upgradable_packages: Mapped[int] = mapped_column(Integer, default=0)
    reboot_required: Mapped[bool] = mapped_column(Boolean, default=False)
    installed_update_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pending_update_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    windows_update_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    os_name: Mapped[str] = mapped_column(String(120))
    os_version: Mapped[str] = mapped_column(String(120))
    kernel_version: Mapped[str] = mapped_column(String(120))
    agent_version: Mapped[str] = mapped_column(String(40))
    execution_mode: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
