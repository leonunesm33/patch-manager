from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.patch_repository import PatchRepository
from app.schemas.auth import UserResponse
from app.schemas.patch import PatchApproval

router = APIRouter()

MOCK_PATCHES = [
    PatchApproval(
        id="KB5034441",
        target="Windows Servers",
        severity="critical",
        machines=8,
        release_date="2026-04-08",
    ),
    PatchApproval(
        id="openssl-3.0.2-0ubuntu1.14",
        target="Ubuntu Production",
        severity="important",
        machines=5,
        release_date="2026-04-09",
    ),
]


@router.get("", response_model=list[PatchApproval])
def list_patch_approvals(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(get_current_user)],
) -> list[PatchApproval]:
    try:
        repository = PatchRepository(db)
        patches = repository.list_all()
        if patches:
            return [
                PatchApproval(
                    id=patch.id,
                    target=patch.target,
                    severity=patch.severity,
                    machines=patch.machines,
                    release_date=patch.release_date.isoformat()
                    if isinstance(patch.release_date, date)
                    else str(patch.release_date),
                )
                for patch in patches
            ]
    except SQLAlchemyError:
        pass

    return MOCK_PATCHES
