from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.schedule import ScheduleModel
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.auth import UserResponse
from app.schemas.schedule import ScheduleCreate, ScheduleItem

router = APIRouter()

MOCK_SCHEDULES = [
    ScheduleItem(
        id="sched-1",
        name="Janela Semanal Linux",
        scope="Ubuntu Production",
        cron_label="Toda quarta, 02:00",
        reboot_policy="Somente se necessario",
    ),
    ScheduleItem(
        id="sched-2",
        name="Patches Criticos Windows",
        scope="Windows Servers",
        cron_label="Diariamente, 03:00",
        reboot_policy="Sempre reiniciar",
    ),
]


@router.get("", response_model=list[ScheduleItem])
def list_schedules(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[ScheduleItem]:
    try:
        repository = ScheduleRepository(db)
        schedules = repository.list_all()
        if schedules:
            return [ScheduleItem.model_validate(schedule) for schedule in schedules]
    except SQLAlchemyError:
        pass

    return MOCK_SCHEDULES


@router.post("", response_model=ScheduleItem, status_code=201)
def create_schedule(
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> ScheduleItem:
    repository = ScheduleRepository(db)
    schedule = repository.add(
        ScheduleModel(
            id=f"sched-{uuid4().hex[:8]}",
            name=payload.name,
            scope=payload.scope,
            cron_label=payload.cron_label,
            reboot_policy=payload.reboot_policy,
        )
    )
    return ScheduleItem.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleItem)
def update_schedule(
    schedule_id: str,
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> ScheduleItem:
    repository = ScheduleRepository(db)
    schedule = repository.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule.name = payload.name
    schedule.scope = payload.scope
    schedule.cron_label = payload.cron_label
    schedule.reboot_policy = payload.reboot_policy

    schedule = repository.update(schedule)
    return ScheduleItem.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> Response:
    repository = ScheduleRepository(db)
    schedule = repository.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    repository.delete(schedule)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
