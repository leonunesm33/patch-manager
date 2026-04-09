from collections.abc import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.core.security import decode_token
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
