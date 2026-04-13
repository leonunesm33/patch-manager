from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.schemas.auth import UserResponse
from app.schemas.report import ReportItem

router = APIRouter()


@router.get("", response_model=list[ReportItem])
def list_reports(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[ReportItem]:
    repository = ExecutionLogRepository(db)
    logs = repository.list_recent()
    return [
        ReportItem(
            date=log.executed_at.strftime("%d/%m %H:%M"),
            schedule=log.schedule_name,
            machine=log.machine_name,
            patch=log.patch_id,
            platform=log.platform,
            severity=log.severity,
            result=log.result,
            duration=f"{log.duration_seconds // 60}m {log.duration_seconds % 60:02d}s",
        )
        for log in logs
    ]
