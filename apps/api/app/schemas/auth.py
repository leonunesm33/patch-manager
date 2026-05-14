from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    must_change_password: bool
    role: str


class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str


class UserProfileUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    avatar_initials: str | None = Field(default=None, max_length=4)
    avatar_color: str | None = Field(default=None, max_length=32)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    full_name: str
    avatar_initials: str | None = None
    avatar_color: str | None = None
    role: str
    is_active: bool
    must_change_password: bool
    password_changed_at: datetime | None = None
