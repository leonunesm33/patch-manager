from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AgentInventoryItemModel(Base):
    __tablename__ = "agent_inventory_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(120), index=True)
    platform: Mapped[str] = mapped_column(String(50), index=True)
    item_type: Mapped[str] = mapped_column(String(20), index=True)
    identifier: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(500))
    current_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    target_version: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source: Mapped[str | None] = mapped_column(String(200), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    kb_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    security_only: Mapped[bool] = mapped_column(Boolean, default=False)
    installed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
