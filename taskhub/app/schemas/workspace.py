from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.core.constants import (
    CANNOT_INVITE_OWNER_ROLE,
    NAME_MIN_LENGTH,
    WORKSPACE_NAME_MAX_LENGTH,
)
from app.models.enums import WorkspaceRole
from app.schemas.base import BaseSchema


class WorkspaceCreate(BaseSchema):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=WORKSPACE_NAME_MAX_LENGTH)


class WorkspaceUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=WORKSPACE_NAME_MAX_LENGTH
    )

    @field_validator("name")
    @classmethod
    def name_cannot_be_null(cls, v):  # noqa: ANN001, ANN206
        if v is None:
            raise ValueError("Không được để null")  # name là NOT NULL (xem review #1)
        return v


class WorkspaceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    owner_id: int
    created_at: datetime


class MemberInvite(BaseSchema):
    email: EmailStr
    role: WorkspaceRole = WorkspaceRole.VIEWER

    @field_validator("role")
    @classmethod
    def cannot_invite_as_owner(cls, v: WorkspaceRole) -> WorkspaceRole:
        if v == WorkspaceRole.OWNER:  # owner là duy nhất, gắn với workspace.owner_id
            raise ValueError(CANNOT_INVITE_OWNER_ROLE)
        return v


class MemberRead(BaseModel):
    user_id: int
    email: str
    full_name: str
    role: WorkspaceRole
