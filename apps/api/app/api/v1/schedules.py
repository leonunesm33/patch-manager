from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator, require_viewer
from app.models.schedule import ScheduleModel
from app.repositories.schedule_repository import ScheduleRepository
from app.schemas.auth import UserResponse
from app.schemas.schedule import ScheduleCreate, ScheduleItem

router = APIRouter()

MOCK_SCHEDULES = [
    ScheduleItem(
        id="sched-1",
        name="Janela Semanal Linux",
        scope="SO: Linux",
        scope_type="os",
        scope_value="Linux",
        cron_label="Semanal, 02:00",
        install_time="02:00",
        reboot_time="03:00",
        recurrence="weekly",
        reboot_policy="Somente se necessario",
    ),
    ScheduleItem(
        id="sched-2",
        name="Patches Criticos Windows",
        scope="Windows Servers",
        scope_type="os",
        scope_value="Windows",
        cron_label="Diariamente, 03:00",
        install_time="03:00",
        reboot_time="04:00",
        recurrence="daily",
        reboot_policy="Sempre reiniciar",
    ),
]


def _normalize_scope_type(scope_type: str) -> str:
    normalized = scope_type.strip().lower()
    return normalized if normalized in {"machine", "group", "os"} else "group"


def _normalize_recurrence(recurrence: str) -> str:
    normalized = recurrence.strip().lower()
    return normalized if normalized in {"once", "daily", "weekly", "monthly"} else "weekly"


def _scope_label(scope_type: str, scope_value: str) -> str:
    labels = {
        "machine": "Maquina",
        "group": "Grupo",
        "os": "SO",
    }
    return f"{labels.get(scope_type, 'Escopo')}: {scope_value}"


def _recurrence_label(recurrence: str) -> str:
    labels = {
        "once": "Unica",
        "daily": "Diaria",
        "weekly": "Semanal",
        "monthly": "Mensal",
    }
    return labels.get(recurrence, recurrence)


def _cron_label(recurrence: str, install_time: str) -> str:
    return f"{_recurrence_label(recurrence)}, {install_time}"


def _reboot_policy_label(reboot_policy: str, reboot_time: str | None) -> str:
    labels = {
        "if-needed": "Reiniciar se necessario",
        "always": "Sempre reiniciar",
        "never": "Nao reiniciar",
    }
    label = labels.get(reboot_policy, reboot_policy)
    if reboot_policy != "never" and reboot_time:
        return f"{label} as {reboot_time}"
    return label


def _apply_payload(schedule: ScheduleModel, payload: ScheduleCreate) -> ScheduleModel:
    scope_type = _normalize_scope_type(payload.scope_type)
    recurrence = _normalize_recurrence(payload.recurrence)
    scope_value = payload.scope_value.strip()
    if not scope_value:
        raise HTTPException(status_code=400, detail="Schedule scope is required")

    schedule.name = payload.name
    schedule.scope_type = scope_type
    schedule.scope_value = scope_value
    schedule.scope = _scope_label(scope_type, schedule.scope_value)
    schedule.install_date = payload.install_date
    schedule.install_time = payload.install_time
    schedule.reboot_date = payload.reboot_date
    schedule.reboot_time = payload.reboot_time if payload.reboot_policy != "never" else None
    schedule.recurrence = recurrence
    schedule.cron_label = _cron_label(recurrence, schedule.install_time)
    schedule.reboot_policy = _reboot_policy_label(payload.reboot_policy, schedule.reboot_time)
    return schedule


@router.get("", response_model=list[ScheduleItem])
def list_schedules(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
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
    _: Annotated[UserResponse, Depends(require_operator)],
) -> ScheduleItem:
    repository = ScheduleRepository(db)
    schedule = repository.add(
        _apply_payload(
            ScheduleModel(
                id=f"sched-{uuid4().hex[:8]}",
                name=payload.name,
                scope="",
                scope_type="group",
                scope_value="",
                cron_label="",
                install_date=None,
                install_time="02:00",
                reboot_date=None,
                reboot_time=None,
                recurrence="weekly",
                reboot_policy="if-needed",
            ),
            payload,
        )
    )
    return ScheduleItem.model_validate(schedule)


@router.put("/{schedule_id}", response_model=ScheduleItem)
def update_schedule(
    schedule_id: str,
    payload: ScheduleCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> ScheduleItem:
    repository = ScheduleRepository(db)
    schedule = repository.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    schedule = _apply_payload(schedule, payload)

    schedule = repository.update(schedule)
    return ScheduleItem.model_validate(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_schedule(
    schedule_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> Response:
    repository = ScheduleRepository(db)
    schedule = repository.get_by_id(schedule_id)
    if schedule is None:
        raise HTTPException(status_code=404, detail="Schedule not found")

    repository.delete(schedule)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
