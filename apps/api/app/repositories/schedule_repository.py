from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.schedule import ScheduleModel


class ScheduleRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[ScheduleModel]:
        return list(self.session.scalars(select(ScheduleModel).order_by(ScheduleModel.name)))

    def add(self, schedule: ScheduleModel) -> ScheduleModel:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def get_by_id(self, schedule_id: str) -> ScheduleModel | None:
        return self.session.get(ScheduleModel, schedule_id)

    def update(self, schedule: ScheduleModel) -> ScheduleModel:
        self.session.add(schedule)
        self.session.commit()
        self.session.refresh(schedule)
        return schedule

    def delete(self, schedule: ScheduleModel) -> None:
        self.session.delete(schedule)
        self.session.commit()
