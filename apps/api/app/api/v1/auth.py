from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.repositories.user_repository import UserRepository
from app.schemas.auth import LoginRequest, TokenResponse, UserResponse
from app.services.auth_service import AuthError, AuthService

router = APIRouter()


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest,
    db: Annotated[Session, Depends(get_db)],
) -> TokenResponse:
    service = AuthService(UserRepository(db))

    try:
        token = service.authenticate(payload.username, payload.password)
    except AuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        ) from exc

    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(current_user: Annotated[UserResponse, Depends(get_current_user)]) -> UserResponse:
    return current_user
