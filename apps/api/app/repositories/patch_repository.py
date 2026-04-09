from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.patch import PatchModel


class PatchRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[PatchModel]:
        return list(self.session.scalars(select(PatchModel).order_by(PatchModel.release_date.desc())))
