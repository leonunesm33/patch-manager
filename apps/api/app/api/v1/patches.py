from datetime import UTC, date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_operator, require_viewer
from app.models.machine import MachineModel
from app.models.patch import PatchModel
from app.repositories.machine_repository import MachineRepository
from app.repositories.patch_repository import PatchRepository
from app.schemas.auth import UserResponse
from app.schemas.patch import PatchAffectedMachine, PatchApproval, PatchCreate

router = APIRouter()

MOCK_PATCHES = [
    PatchApproval(
        id="KB5034441",
        target="Windows Servers",
        severity="critical",
        category="security",
        machines=8,
        affected_machines=[],
        release_date="2026-04-08",
        approval_status="pending",
    ),
    PatchApproval(
        id="openssl-3.0.2-0ubuntu1.14",
        target="Ubuntu Production",
        severity="high",
        category="security",
        machines=5,
        affected_machines=[],
        release_date="2026-04-09",
        approval_status="pending",
    ),
]


def _machine_matches_patch_target(machine: MachineModel, target: str) -> bool:
    normalized_target = target.lower()
    platform = machine.platform.lower()
    environment = machine.environment.lower()
    group = machine.group.lower()
    name = machine.name.lower()

    if "windows" in normalized_target and "windows" not in platform:
        return False
    if "ubuntu" in normalized_target and "ubuntu" not in platform:
        return False
    if "debian" in normalized_target and "debian" not in platform:
        return False
    if "rhel" in normalized_target and "rhel" not in platform:
        return False
    if "linux" in normalized_target and all(item not in platform for item in ("ubuntu", "debian", "rhel", "linux")):
        return False
    if "production" in normalized_target and environment != "production":
        return False
    if "homolog" in normalized_target and environment != "homolog":
        return False
    if "development" in normalized_target and environment != "development":
        return False

    searchable = " ".join([machine.id, name, platform, environment, group])
    meaningful_tokens = [
        token
        for token in normalized_target.replace("-", " ").split()
        if token not in {"servers", "server", "workstations", "workstation", "hosts", "host"}
    ]
    if not meaningful_tokens:
        return True

    return any(token in searchable for token in meaningful_tokens)


def _affected_machine_response(machine: MachineModel) -> PatchAffectedMachine:
    return PatchAffectedMachine(
        id=machine.id,
        name=machine.name,
        ip=machine.ip,
        platform=machine.platform,
        environment=machine.environment,
        group=machine.group,
        status=machine.status,
    )


def _patch_response(patch: PatchModel, machines: list[MachineModel]) -> PatchApproval:
    affected = [machine for machine in machines if _machine_matches_patch_target(machine, patch.target)]
    return PatchApproval(
        id=patch.id,
        target=patch.target,
        severity=patch.severity,
        category=patch.category,
        machines=len(affected) if affected else patch.machines,
        affected_machines=[_affected_machine_response(machine) for machine in affected],
        release_date=patch.release_date,
        approval_status=patch.approval_status,
        reviewed_by=patch.reviewed_by,
        reviewed_at=patch.reviewed_at,
    )


@router.get("", response_model=list[PatchApproval])
def list_patch_approvals(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_viewer)],
    machine_id: Annotated[str | None, Query()] = None,
    approval_status: Annotated[str | None, Query()] = None,
) -> list[PatchApproval]:
    try:
        repository = PatchRepository(db)
        machine_repository = MachineRepository(db)
        patches = repository.list_all()
        machines = machine_repository.list_all()
        if patches:
            response = [_patch_response(patch, machines) for patch in patches]
            if approval_status:
                response = [patch for patch in response if patch.approval_status == approval_status]
            if machine_id:
                response = [
                    patch
                    for patch in response
                    if any(machine.id == machine_id for machine in patch.affected_machines)
                ]
            return response
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
            category=payload.category,
            machines=payload.machines,
            release_date=payload.release_date,
            approval_status="pending",
            reviewed_by=None,
            reviewed_at=None,
        )
    )
    return _patch_response(patch, MachineRepository(db).list_all())


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
    patch.category = payload.category
    patch.machines = payload.machines
    patch.release_date = payload.release_date

    patch = repository.update(patch)
    return _patch_response(patch, MachineRepository(db).list_all())


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
    return _patch_response(patch, MachineRepository(db).list_all())


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
    return _patch_response(patch, MachineRepository(db).list_all())
