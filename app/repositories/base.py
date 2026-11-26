"""BaseRepository[T]: CRUD + phân trang + Unit-of-Work flush/commit dùng chung cho mọi model."""

import builtins
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def list(self, skip: int = 0, limit: int = 20, *filters: Any) -> builtins.list[ModelT]:
        stmt = (
            select(self.model)
            .where(*filters)
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return builtins.list(result.all())

    async def count(self, *filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).where(*filters)
        return await self.session.scalar(stmt) or 0

    async def paginate(
        self, skip: int = 0, limit: int = 20, *filters: Any
    ) -> tuple[builtins.list[ModelT], int]:
        """Trả về cặp (items, total) chuẩn hoá cho PaginatedResponse.create()."""
        items = await self.list(skip, limit, *filters)
        total = await self.count(*filters)
        return items, total

    async def flush(self) -> None:
        """Đẩy thay đổi xuống DB trong cùng transaction (Unit-of-Work) mà chưa commit."""
        await self.session.flush()

    async def create(self, data: dict[str, Any], *, commit: bool = True) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        if commit:
            await self.session.commit()
            await self.session.refresh(obj)  # nạp lại giá trị server_default (created_at)
        else:
            await self.session.flush()
        return obj

    async def update(self, obj: ModelT, data: dict[str, Any], *, commit: bool = True) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        if commit:
            await self.session.commit()
            await self.session.refresh(obj)
        else:
            await self.session.flush()
        return obj

    async def delete(self, obj: ModelT, *, commit: bool = True) -> None:
        await self.session.delete(obj)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
