from app.core.security import create_access_token, verify_password
from app.models.user import UserModel
from app.repositories.user_repository import UserRepository


class AuthError(Exception):
    pass


class AuthService:
    def __init__(self, user_repository: UserRepository) -> None:
        self.user_repository = user_repository

    def authenticate(self, username: str, password: str) -> str:
        user = self.user_repository.get_by_username(username)
        if user is None or not user.is_active:
            raise AuthError("Invalid credentials")

        if not verify_password(password, user.password_hash):
            raise AuthError("Invalid credentials")

        return create_access_token(user.username)

    def get_user(self, username: str) -> UserModel | None:
        return self.user_repository.get_by_username(username)
