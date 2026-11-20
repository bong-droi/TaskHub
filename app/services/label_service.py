from sqlalchemy.exc import IntegrityError

from app.core.constants import (
    LABEL_NAME_EXISTS,
    LABEL_NOT_FOUND,
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.core.permissions import READ_ROLES, WRITE_ROLES
from app.models import Label, Project, User
from app.models.enums import ProjectStatus
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.access import AccessControl


class LabelService:
    def __init__(
        self, labels: LabelRepository, projects: ProjectRepository, access: AccessControl
    ) -> None:
        self.labels = labels
        self.projects = projects
        self.access = access

    async def _project(self, user: User, project_id: int, allowed) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self.access.require(user, project.workspace_id, allowed, PROJECT_NOT_FOUND)
        return project

    async def _load(self, user: User, label_id: int, allowed) -> tuple[Label, Project]:
        label = await self.labels.get(label_id)
        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND)
        project = await self.projects.get(label.project_id)
        await self.access.require(user, project.workspace_id, allowed, LABEL_NOT_FOUND)
        return label, project

    @staticmethod
    def _ensure_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)

    async def _ensure_unique_name(self, project_id: int, name: str, except_id: int | None = None):
        existing = await self.labels.get_by_name(project_id, name)
        if existing is not None and existing.id != except_id:
            raise ConflictException(LABEL_NAME_EXISTS)

    async def create(self, user: User, project_id: int, payload: LabelCreate) -> Label:
        project = await self._project(user, project_id, WRITE_ROLES)
        self._ensure_active(project)
        await self._ensure_unique_name(project_id, payload.name)
        try:
            return await self.labels.create({"project_id": project_id, **payload.model_dump()})
        except IntegrityError:  # 2 request tạo cùng tên một lúc: ràng buộc DB chặn
            await self.labels.session.rollback()
            raise ConflictException(LABEL_NAME_EXISTS) from None

    async def list_in_project(
        self, user: User, project_id: int, skip: int, limit: int
    ) -> tuple[list[Label], int]:
        await self._project(user, project_id, READ_ROLES)
        return (
            await self.labels.list_by_project(project_id, skip, limit),
            await self.labels.count_by_project(project_id),
        )

    async def update(self, user: User, label_id: int, payload: LabelUpdate) -> Label:
        label, project = await self._load(user, label_id, WRITE_ROLES)
        self._ensure_active(project)
        data = payload.model_dump(exclude_unset=True)
        if "name" in data:
            await self._ensure_unique_name(project.id, data["name"], except_id=label.id)
        return await self.labels.update(label, data)

    async def delete(self, user: User, label_id: int) -> None:
        label, _ = await self._load(user, label_id, WRITE_ROLES)
        await self.labels.delete(label)  # các task đang gắn label này tự được gỡ
