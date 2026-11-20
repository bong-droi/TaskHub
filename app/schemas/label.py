from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    DEFAULT_LABEL_COLOR,
    LABEL_COLOR_PATTERN,
    LABEL_NAME_MAX_LENGTH,
    NAME_MIN_LENGTH,
)
from app.schemas.base import BaseSchema

ColorField = Field(pattern=LABEL_COLOR_PATTERN, examples=["#FF5733"])


class LabelCreate(BaseSchema):
    name: str = Field(min_length=NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH)
    color: str = Field(default=DEFAULT_LABEL_COLOR, pattern=LABEL_COLOR_PATTERN)


class LabelUpdate(BaseSchema):
    name: str | None = Field(
        default=None, min_length=NAME_MIN_LENGTH, max_length=LABEL_NAME_MAX_LENGTH
    )
    color: str | None = Field(default=None, pattern=LABEL_COLOR_PATTERN)

    @field_validator("name", "color")
    @classmethod
    def required_fields_cannot_be_null(cls, v):  # noqa: ANN001, ANN206
        if v is None:  # name/color là NOT NULL (xem review #1)
            raise ValueError("Không được để null")
        return v


class LabelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    color: str
