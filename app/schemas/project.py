from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    NAME_MIN_LENGTH,
    PROJECT_DESCRIPTION_MAX_LENGTH,
    PROJECT_NAME_MAX_LENGTH,
)
from app.models.enums import ProjectStatus
from app.schemas.base import BaseSchema


class ProjectCreate(BaseSchema):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH)
    description: str | None = Field(default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH)


class ProjectUpdate(BaseSchema):
    """`status` cố ý không có ở đây: đổi trạng thái đi qua endpoint /archive."""

    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=PROJECT_NAME_MAX_LENGTH
    )
    description: str | None = Field(default=None, max_length=PROJECT_DESCRIPTION_MAX_LENGTH)

    @field_validator("name")
    @classmethod
    def name_cannot_be_null(cls, v):  # noqa: ANN001, ANN206
        if v is None:
            raise ValueError("Không được để null")
        return v


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workspace_id: int
    name: str
    description: str | None
    status: ProjectStatus
    created_at: datetime
