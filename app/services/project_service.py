from app.core.permissions import MANAGE_ROLES, READ_ROLES, WRITE_ROLES
from app.models import Project, User
from app.models.enums import ProjectStatus
from app.repositories.project_repository import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.resource_access import ResourceAccess
from app.services.task_cache import TaskListCache


class ProjectService:
    def __init__(
        self, projects: ProjectRepository, resources: ResourceAccess, cache: TaskListCache
    ) -> None:
        self.projects = projects
        self.resources = resources
        self.cache = cache

    async def create(self, user: User, workspace_id: int, payload: ProjectCreate) -> Project:
        await self.resources.workspace(user, workspace_id, WRITE_ROLES)
        project = await self.projects.create({"workspace_id": workspace_id, **payload.model_dump()})
        # SQLite có thể dùng lại id của project đã xoá: đổi version để không dính cache cũ
        await self.cache.invalidate(project.id)
        return project

    async def list_in_workspace(
        self, user: User, workspace_id: int, skip: int, limit: int
    ) -> tuple[list[Project], int]:
        await self.resources.workspace(user, workspace_id, READ_ROLES)
        return (
            await self.projects.list_by_workspace(workspace_id, skip, limit),
            await self.projects.count_by_workspace(workspace_id),
        )

    async def get(self, user: User, project_id: int) -> Project:
        return await self.resources.project(user, project_id, READ_ROLES)

    async def update(self, user: User, project_id: int, payload: ProjectUpdate) -> Project:
        project = await self.resources.project(user, project_id, WRITE_ROLES)
        self.resources.ensure_active(project)
        return await self.projects.update(project, payload.model_dump(exclude_unset=True))

    async def archive(self, user: User, project_id: int) -> Project:
        project = await self.resources.project(user, project_id, WRITE_ROLES)
        if project.status == ProjectStatus.ARCHIVED:
            return project  # idempotent
        return await self.projects.update(project, {"status": ProjectStatus.ARCHIVED})

    async def delete(self, user: User, project_id: int) -> None:
        project = await self.resources.project(user, project_id, MANAGE_ROLES)
        await self.projects.delete(project)
        await self.cache.invalidate(project_id)
