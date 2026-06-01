from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.machine_group import MachineGroupModel


class MachineGroupRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[MachineGroupModel]:
        statement = select(MachineGroupModel).order_by(MachineGroupModel.name)
        return list(self.session.scalars(statement))

    def get_by_id(self, group_id: str) -> MachineGroupModel | None:
        return self.session.get(MachineGroupModel, group_id)

    def get_by_name(self, name: str) -> MachineGroupModel | None:
        statement = select(MachineGroupModel).where(MachineGroupModel.name == name)
        return self.session.scalar(statement)

    def add(self, group: MachineGroupModel) -> MachineGroupModel:
        self.session.add(group)
        self.session.commit()
        self.session.refresh(group)
        return group

    def delete(self, group: MachineGroupModel) -> None:
        self.session.delete(group)
        self.session.commit()
