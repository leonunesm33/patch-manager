from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import UserModel


class UserRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_username(self, username: str) -> UserModel | None:
        query = select(UserModel).where(UserModel.username == username)
        return self.session.scalar(query)

    def add(self, user: UserModel) -> UserModel:
        self.session.add(user)
        self.session.flush()
        return user

    def update(self, user: UserModel) -> UserModel:
        self.session.add(user)
        self.session.commit()
        self.session.refresh(user)
        return user
