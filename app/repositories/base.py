"""BaseRepository[T]: CRUD + phân trang dùng chung cho mọi model."""
from typing import Any, Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, obj_id: int) -> ModelT | None:
        return await self.session.get(self.model, obj_id)

    async def list(self, skip: int = 0, limit: int = 20, *filters: Any) -> list[ModelT]:
        stmt = (
            select(self.model)
            .where(*filters)
            .order_by(self.model.id)  # type: ignore[attr-defined]
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self, *filters: Any) -> int:
        stmt = select(func.count()).select_from(self.model).where(*filters)
        return await self.session.scalar(stmt) or 0

    async def create(self, data: dict[str, Any]) -> ModelT:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.commit()
        await self.session.refresh(obj)  # nạp lại giá trị server_default (created_at)
        return obj

    async def update(self, obj: ModelT, data: dict[str, Any]) -> ModelT:
        for key, value in data.items():
            setattr(obj, key, value)
        await self.session.commit()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.commit()
