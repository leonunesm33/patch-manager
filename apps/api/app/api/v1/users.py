from datetime import UTC, datetime
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_admin
from app.core.security import hash_password
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse
from app.schemas.user import (
    UserAdminCreateRequest,
    UserAdminPasswordResetRequest,
    UserAdminResponse,
    UserAdminUpdateRequest,
    UserRoleResponse,
)

router = APIRouter()

USER_ROLES = [
    UserRoleResponse(
        value="admin",
        label="Administrador",
        description="Acesso total, incluindo configuracoes, agentes e gestao de usuarios.",
    ),
    UserRoleResponse(
        value="user",
        label="Usuario",
        description="Acesso operacional sem permissao para gerenciar usuarios ou configuracoes administrativas.",
    ),
]


@router.get("/roles", response_model=list[UserRoleResponse])
def list_user_roles(_: Annotated[UserResponse, Depends(require_admin)]) -> list[UserRoleResponse]:
    return USER_ROLES


@router.get("", response_model=list[UserAdminResponse])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_admin)],
) -> list[UserAdminResponse]:
    return [UserAdminResponse.model_validate(user) for user in UserRepository(db).list_all()]


@router.post("", response_model=UserAdminResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserAdminCreateRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_admin)],
) -> UserAdminResponse:
    repository = UserRepository(db)
    username = payload.username.strip().lower()
    if repository.get_by_username(username) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    user = UserModel(
        id=f"user-{uuid4().hex[:12]}",
        username=username,
        full_name=payload.full_name.strip(),
        avatar_initials=payload.avatar_initials.strip().upper() if payload.avatar_initials else None,
        avatar_color=payload.avatar_color.strip() if payload.avatar_color else None,
        password_hash=hash_password(payload.password),
        role=payload.role,
        is_active=payload.is_active,
        must_change_password=payload.must_change_password,
        password_changed_at=None,
    )
    repository.add(user)
    db.commit()
    db.refresh(user)
    return UserAdminResponse.model_validate(user)


@router.patch("/{user_id}", response_model=UserAdminResponse)
def update_user(
    user_id: str,
    payload: UserAdminUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(require_admin)],
) -> UserAdminResponse:
    repository = UserRepository(db)
    user = repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    if user.username == current_user.username and (not payload.is_active or payload.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The current admin cannot disable or demote their own account",
        )

    user.full_name = payload.full_name.strip()
    user.role = payload.role
    user.avatar_initials = payload.avatar_initials.strip().upper() if payload.avatar_initials else None
    user.avatar_color = payload.avatar_color.strip() if payload.avatar_color else None
    user.is_active = payload.is_active
    user.must_change_password = payload.must_change_password
    return UserAdminResponse.model_validate(repository.update(user))


@router.post("/{user_id}/reset-password", response_model=UserAdminResponse)
def reset_user_password(
    user_id: str,
    payload: UserAdminPasswordResetRequest,
    db: Annotated[Session, Depends(get_db)],
    _: Annotated[UserResponse, Depends(require_admin)],
) -> UserAdminResponse:
    repository = UserRepository(db)
    user = repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.password_hash = hash_password(payload.new_password)
    user.must_change_password = payload.must_change_password
    user.password_changed_at = datetime.now(UTC)
    return UserAdminResponse.model_validate(repository.update(user))
