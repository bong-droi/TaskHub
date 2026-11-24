from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    DEFAULT_LABEL_COLOR,
    LABEL_COLOR_PATTERN,
    LABEL_NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)
from app.schemas.base import BaseSchema, not_nullable


class LabelCreate(BaseSchema):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(default=DEFAULT_LABEL_COLOR, pattern=LABEL_COLOR_PATTERN)


class LabelUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH
    )
    color: str | None = Field(default=None, pattern=LABEL_COLOR_PATTERN)

    _no_null = not_nullable("name", "color")


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
