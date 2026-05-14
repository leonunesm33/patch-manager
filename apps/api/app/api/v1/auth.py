from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginRequest,
    PasswordChangeRequest,
    TokenResponse,
    UserProfileUpdateRequest,
    UserResponse,
)
from app.services.auth_service import AuthError, AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(UserRepository(db))

    try:
        user, token = service.authenticate(payload.username, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc

    return TokenResponse(
        access_token=token,
        must_change_password=user.must_change_password,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_me(
    payload: UserProfileUpdateRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    repository = UserRepository(db)
    user = repository.get_by_username(current_user.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.full_name = payload.full_name.strip()
    user.avatar_initials = payload.avatar_initials.strip().upper() if payload.avatar_initials else None
    user.avatar_color = payload.avatar_color.strip() if payload.avatar_color else None
    updated_user = repository.update(user)
    return UserResponse.model_validate(updated_user)


@router.post("/change-password", response_model=UserResponse)
def change_password(
    payload: PasswordChangeRequest,
    db: Annotated[Session, Depends(get_db)],
    current_user: Annotated[UserResponse, Depends(get_current_user)],
) -> UserResponse:
    repository = UserRepository(db)
    user = repository.get_by_username(current_user.username)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    service = AuthService(repository)
    try:
        updated_user = service.change_password(user, payload.current_password, payload.new_password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UserResponse.model_validate(updated_user)
