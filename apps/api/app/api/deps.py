from collections.abc import Generator
from typing import Callable

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.config import settings
from app.core.security import decode_token, verify_password
from app.models.agent_credential import AgentCredentialModel
from app.repositories.agent_credential_repository import AgentCredentialRepository
from app.services.settings_service import SettingsService
from app.repositories.user_repository import UserRepository
from app.schemas.auth import UserResponse


def get_db() -> Generator[Session, None, None]:
    yield from get_db_session()


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> UserResponse:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
    )

    try:
        payload = decode_token(token)
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError as exc:
        raise credentials_exception from exc

    repository = UserRepository(db)
    user = repository.get_by_username(username)
    if user is None or not user.is_active:
        raise credentials_exception

    return UserResponse.model_validate(user)


ROLE_LEVELS = {
    "viewer": 10,
    "operator": 20,
    "admin": 30,
}


def require_role(minimum_role: str) -> Callable[[UserResponse], UserResponse]:
    def dependency(current_user: UserResponse = Depends(get_current_user)) -> UserResponse:
        user_level = ROLE_LEVELS.get(current_user.role, 0)
        required_level = ROLE_LEVELS.get(minimum_role, 0)
        if user_level < required_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires {minimum_role} role",
            )
        return current_user

    return dependency


require_viewer = require_role("viewer")
require_operator = require_role("operator")
require_admin = require_role("admin")


def get_agent_identity(
    x_agent_id: str = Header(default=""),
    x_agent_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> AgentCredentialModel:
    repository = AgentCredentialRepository(db)
    credential = repository.get_by_agent_id(x_agent_id)
    if (
        credential is None
        or not credential.is_active
        or not verify_password(x_agent_key, credential.key_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid agent credentials",
        )
    return credential


def get_bootstrap_token(
    x_bootstrap_token: str = Header(default=""),
    db: Session = Depends(get_db),
) -> str:
    settings_service = SettingsService(db)
    expected_token = settings_service.get_agent_bootstrap_token()
    if settings_service.get_agent_bootstrap_token_is_expired():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bootstrap token expired",
        )
    if x_bootstrap_token != expected_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bootstrap token",
        )
    return x_bootstrap_token
