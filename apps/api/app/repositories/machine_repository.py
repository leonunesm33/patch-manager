from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.machine import MachineModel


class MachineRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[MachineModel]:
        return list(self.session.scalars(select(MachineModel).order_by(MachineModel.name)))

    def get_by_id(self, machine_id: str) -> MachineModel | None:
        return self.session.get(MachineModel, machine_id)

    def get_by_name(self, machine_name: str) -> MachineModel | None:
        statement = select(MachineModel).where(MachineModel.name == machine_name)
        return self.session.scalar(statement)

    def list_groups(self) -> list[str]:
        statement = select(MachineModel.group).distinct().order_by(MachineModel.group)
        return [group_name for group_name in self.session.scalars(statement) if group_name]

    def add(self, machine: MachineModel) -> MachineModel:
        self.session.add(machine)
        self.session.commit()
        self.session.refresh(machine)
        return machine

    def update(self, machine: MachineModel) -> MachineModel:
        self.session.add(machine)
        self.session.commit()
        self.session.refresh(machine)
        return machine

    def delete(self, machine: MachineModel) -> None:
        self.session.delete(machine)
        self.session.commit()
