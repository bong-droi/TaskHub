import math

from pydantic import BaseModel, computed_field


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    limit: int

    @computed_field  # type: ignore[prop-decorator]
    @property
    def pages(self) -> int:
        return math.ceil(self.total / self.limit) if self.limit else 0
