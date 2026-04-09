from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi import Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.machine import MachineModel
from app.repositories.machine_repository import MachineRepository
from app.schemas.auth import UserResponse
from app.schemas.machine import Machine, MachineCreate

router = APIRouter()

MOCK_MACHINES = [
    Machine(
        id="srv-web-01",
        name="SRV-WEB-01",
        ip="10.0.1.21",
        platform="Windows",
        group="Web Servers",
        status="online",
        pending_patches=4,
        last_check_in="2026-04-09T14:12:00Z",
        risk="critical",
    ),
    Machine(
        id="ubuntu-prod-03",
        name="ubuntu-prod-03",
        ip="10.1.4.33",
        platform="Ubuntu",
        group="Linux Production",
        status="online",
        pending_patches=3,
        last_check_in="2026-04-09T14:10:00Z",
        risk="important",
    ),
    Machine(
        id="srv-db-02",
        name="SRV-DB-02",
        ip="10.0.2.11",
        platform="Windows",
        group="Database",
        status="warning",
        pending_patches=7,
        last_check_in="2026-04-09T13:58:00Z",
        risk="critical",
    ),
]


@router.get("", response_model=list[Machine])
def list_machines(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[Machine]:
    try:
        repository = MachineRepository(db)
        machines = repository.list_all()
        if machines:
            return [Machine.model_validate(machine) for machine in machines]
    except SQLAlchemyError:
        pass

    return MOCK_MACHINES


@router.get("/{machine_id}", response_model=Machine)
def get_machine(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    try:
        repository = MachineRepository(db)
        machine = repository.get_by_id(machine_id)
        if machine is not None:
            return Machine.model_validate(machine)
    except SQLAlchemyError:
        pass

    for machine in MOCK_MACHINES:
        if machine.id == machine_id:
            return machine

    raise HTTPException(status_code=404, detail="Machine not found")


@router.post("", response_model=Machine, status_code=201)
def create_machine(
    payload: MachineCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    repository = MachineRepository(db)
    machine = repository.add(
        MachineModel(
            id=f"machine-{uuid4().hex[:8]}",
            name=payload.name,
            ip=payload.ip,
            platform=payload.platform,
            group=payload.group,
            status=payload.status,
            pending_patches=payload.pending_patches,
            last_check_in=datetime.now(UTC),
            risk=payload.risk,
        )
    )
    return Machine.model_validate(machine)


@router.put("/{machine_id}", response_model=Machine)
def update_machine(
    machine_id: str,
    payload: MachineCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Machine:
    repository = MachineRepository(db)
    machine = repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    machine.name = payload.name
    machine.ip = payload.ip
    machine.platform = payload.platform
    machine.group = payload.group
    machine.status = payload.status
    machine.pending_patches = payload.pending_patches
    machine.risk = payload.risk
    machine.last_check_in = datetime.now(UTC)

    machine = repository.update(machine)
    return Machine.model_validate(machine)


@router.delete("/{machine_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_machine(
    machine_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Response:
    repository = MachineRepository(db)
    machine = repository.get_by_id(machine_id)
    if machine is None:
        raise HTTPException(status_code=404, detail="Machine not found")

    repository.delete(machine)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
