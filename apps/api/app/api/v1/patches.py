from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator, require_viewer
from app.models.patch import PatchModel
from app.repositories.patch_repository import PatchRepository
from app.schemas.auth import UserResponse
from app.schemas.patch import PatchApproval, PatchCreate

router = APIRouter()

MOCK_PATCHES = [
    PatchApproval(
        id="KB5034441",
        target="Windows Servers",
        severity="critical",
        machines=8,
        release_date="2026-04-08",
        approval_status="pending",
    ),
    PatchApproval(
        id="openssl-3.0.2-0ubuntu1.14",
        target="Ubuntu Production",
        severity="important",
        machines=5,
        release_date="2026-04-09",
        approval_status="pending",
    ),
]


@router.get("", response_model=list[PatchApproval])
def list_patch_approvals(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
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
                    approval_status=patch.approval_status,
                    reviewed_by=patch.reviewed_by,
                    reviewed_at=patch.reviewed_at,
                )
                for patch in patches
            ]
    except SQLAlchemyError:
        pass

    return MOCK_PATCHES


@router.post("", response_model=PatchApproval, status_code=201)
def create_patch(
    payload: PatchCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> PatchApproval:
    repository = PatchRepository(db)
    if repository.get_by_id(payload.id) is not None:
        raise HTTPException(status_code=409, detail="Patch already exists")

    patch = repository.update(
        PatchModel(
            id=payload.id,
            target=payload.target,
            severity=payload.severity,
            machines=payload.machines,
            release_date=payload.release_date,
            approval_status="pending",
            reviewed_by=None,
            reviewed_at=None,
        )
    )
    return PatchApproval.model_validate(patch)


@router.put("/{patch_id}", response_model=PatchApproval)
def update_patch(
    patch_id: str,
    payload: PatchCreate,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> PatchApproval:
    repository = PatchRepository(db)
    patch = repository.get_by_id(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    if payload.id != patch_id and repository.get_by_id(payload.id) is not None:
        raise HTTPException(status_code=409, detail="Patch already exists")

    patch.id = payload.id
    patch.target = payload.target
    patch.severity = payload.severity
    patch.machines = payload.machines
    patch.release_date = payload.release_date

    patch = repository.update(patch)
    return PatchApproval.model_validate(patch)


@router.delete("/{patch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patch(
    patch_id: str,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_operator)],
) -> Response:
    repository = PatchRepository(db)
    patch = repository.get_by_id(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    db.delete(patch)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{patch_id}/approve", response_model=PatchApproval)
def approve_patch(
    patch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_operator)],
) -> PatchApproval:
    repository = PatchRepository(db)
    patch = repository.get_by_id(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    patch.approval_status = "approved"
    patch.reviewed_by = current_user.username
    patch.reviewed_at = datetime.now(UTC)

    patch = repository.update(patch)
    return PatchApproval.model_validate(patch)


@router.post("/{patch_id}/reject", response_model=PatchApproval)
def reject_patch(
    patch_id: str,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_operator)],
) -> PatchApproval:
    repository = PatchRepository(db)
    patch = repository.get_by_id(patch_id)
    if patch is None:
        raise HTTPException(status_code=404, detail="Patch not found")

    patch.approval_status = "rejected"
    patch.reviewed_by = current_user.username
    patch.reviewed_at = datetime.now(UTC)

    patch = repository.update(patch)
    return PatchApproval.model_validate(patch)
