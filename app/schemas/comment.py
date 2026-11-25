from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import COMMENT_MAX_LENGTH, NAME_MIN_LENGTH
from app.schemas.base import BaseSchema


class CommentCreate(BaseSchema):
    content: str = Field(min_length=NAME_MIN_LENGTH, max_length=COMMENT_MAX_LENGTH)


class CommentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    task_id: int
    author_id: int
    content: str
    created_at: datetime
