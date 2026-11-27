import math
from collections.abc import Sequence

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

    @classmethod
    def create(
        cls,
        items: Sequence[T],
        total: int,
        page: int,
        limit: int,
    ) -> "Page[T]":
        """Factory chuẩn hoá phân trang từ cặp (items, total) của repository/service."""
        return cls(items=list(items), total=total, page=page, limit=limit)
