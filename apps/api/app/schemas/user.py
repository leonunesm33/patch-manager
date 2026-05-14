from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserRoleResponse(BaseModel):
    value: str
    label: str
    description: str


class UserAdminCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    full_name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=10, max_length=128)
    role: str = Field(pattern="^(admin|user)$")
    avatar_initials: str | None = Field(default=None, max_length=4)
    avatar_color: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    must_change_password: bool = True


class UserAdminUpdateRequest(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    role: str = Field(pattern="^(admin|user)$")
    avatar_initials: str | None = Field(default=None, max_length=4)
    avatar_color: str | None = Field(default=None, max_length=32)
    is_active: bool = True
    must_change_password: bool = False


class UserAdminPasswordResetRequest(BaseModel):
    new_password: str = Field(min_length=10, max_length=128)
    must_change_password: bool = True


class UserAdminResponse(BaseModel):
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
    created_at: datetime
