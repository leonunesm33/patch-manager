from datetime import UTC, datetime

from app.core.security import create_access_token, verify_password
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository
from app.core.security import hash_password


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def authenticate(self, username: str, password: str) -> tuple[UserModel, str]:
        user = self.user_repository.get_by_username(username)
        if user is None or not user.is_active:
            raise AuthError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")

        return user, create_access_token(user.username)

    def get_user(self, username: str) -> UserModel | None:
        return self.user_repository.get_by_username(username)

    def change_password(self, user: UserModel, current_password: str, new_password: str) -> UserModel:
        if not verify_password(current_password, user.password_hash):
            raise AuthError("Invalid credentials")
        if len(new_password) < 10:
            raise AuthError("New password must have at least 10 characters")
        if current_password == new_password:
            raise AuthError("New password must be different from the current password")

        user.password_hash = hash_password(new_password)
        user.must_change_password = False
        user.password_changed_at = datetime.now(UTC)
        return self.user_repository.update(user)
