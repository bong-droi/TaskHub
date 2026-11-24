from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    NAME_MIN_LENGTH,
    PROJECT_DESCRIPTION_MAX_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
)
from app.models.enums import ProjectStatus
from app.schemas.base import BaseSchema, not_nullable


class ProjectCreate(BaseSchema):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH)


class ProjectUpdate(BaseSchema):
    """`status` cố ý không có ở đây: đổi trạng thái đi qua endpoint /archive."""

    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH
    )
    description: str | None = Field(default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH)

    _no_null = not_nullable("name")


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
