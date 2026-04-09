from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.schemas.auth import UserResponse
from app.schemas.report import ReportItem

router = APIRouter()


@router.get("", response_model=list[ReportItem])
def list_reports(
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[ReportItem]:
    return [
        ReportItem(
            date="09/04 14:10",
            machine="SRV-WEB-01",
            patch="KB5034441",
            platform="Windows",
            severity="critical",
            result="applied",
            duration="4m 12s",
        ),
        ReportItem(
            date="09/04 13:55",
            machine="ubuntu-prod-03",
            patch="linux-image-6.5.0-44",
            platform="Ubuntu",
            severity="critical",
            result="applied",
            duration="8m 30s",
        ),
        ReportItem(
            date="09/04 13:40",
            machine="SRV-DB-02",
            patch="KB5034122",
            platform="Windows",
            severity="critical",
            result="failed",
            duration="2m 01s",
        ),
    ]
