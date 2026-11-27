from sqlalchemy.exc import IntegrityError

from app.core.constants import LABEL_NAME_EXISTS
from app.core.exceptions import ConflictException
from app.core.permissions import READ_ROLES, WRITE_ROLES
from app.models import Label, User
from app.repositories.label_repository import LabelRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.resource_access import ResourceAccess
from app.services.task_cache import TaskListCache


class LabelService:
    def __init__(
        self, labels: LabelRepository, resources: ResourceAccess, cache: TaskListCache
    ) -> None:
        self.labels = labels
        self.resources = resources
        self.cache = cache

    async def _ensure_unique_name(self, project_id: int, name: str, except_id: int | None = None):
        existing = await self.labels.get_by_name(project_id, name)
        if existing is not None and existing.id != except_id:
            raise ConflictException(LABEL_NAME_EXISTS)

    async def create(self, user: User, project_id: int, payload: LabelCreate) -> Label:
        project = await self.resources.project(user, project_id, WRITE_ROLES)
        self.resources.ensure_active(project)
        await self._ensure_unique_name(project_id, payload.name)
        try:
            return await self.labels.create({"project_id": project_id, **payload.model_dump()})
        except IntegrityError:  # 2 request tạo cùng tên một lúc: unique index của DB chặn bản sau
            await self.labels.session.rollback()
            raise ConflictException(LABEL_NAME_EXISTS) from None

    async def list_in_project(
        self, user: User, project_id: int, skip: int, limit: int
    ) -> tuple[list[Label], int]:
        await self.resources.project(user, project_id, READ_ROLES)
        return (
            await self.labels.list_by_project(project_id, skip, limit),
            await self.labels.count_by_project(project_id),
        )

    async def update(self, user: User, label_id: int, payload: LabelUpdate) -> Label:
        ctx = await self.resources.label(user, label_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            await self._ensure_unique_name(ctx.project.id, data["name"], except_id=ctx.label.id)
        try:
            updated = await self.labels.update(ctx.label, data)
        except IntegrityError:  # đổi tên trùng nhau cùng lúc: cũng phải trả 409 chứ không phải 500
            await self.labels.session.rollback()
            raise ConflictException(LABEL_NAME_EXISTS) from None
        await self.cache.invalidate(ctx.project.id)  # tên/màu label hiển thị trong task đã cache
        return updated

    async def delete(self, user: User, label_id: int) -> None:
        ctx = await self.resources.label(user, label_id, WRITE_ROLES)
        await self.labels.delete(ctx.label)  # các task đang gắn label này tự được gỡ
        await self.cache.invalidate(ctx.project.id)
