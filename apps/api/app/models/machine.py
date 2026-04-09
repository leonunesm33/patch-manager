from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MachineModel(Base):
    __tablename__ = "machines"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    ip: Mapped[str] = mapped_column(String(45))
    platform: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(30))
