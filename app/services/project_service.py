from app.core.constants import PROJECT_ARCHIVED, PROJECT_NOT_FOUND, WORKSPACE_NOT_FOUND
from app.core.exceptions import ConflictException, NotFoundException
from app.core.permissions import MANAGE_ROLES, READ_ROLES, WRITE_ROLES
from app.models import Project, User
from app.models.enums import ProjectStatus
from app.repositories.project_repository import ProjectRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.services.access import AccessControl


class ProjectService:
    def __init__(
        self,
        projects: ProjectRepository,
        workspaces: WorkspaceRepository,
        access: AccessControl,
    ) -> None:
        self.projects = projects
        self.workspaces = workspaces
        self.access = access

    async def _workspace_access(self, user: User, workspace_id: int, allowed) -> None:
        if await self.workspaces.get(workspace_id) is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND)
        await self.access.require(user, workspace_id, allowed, WORKSPACE_NOT_FOUND)

    async def _load(self, user: User, project_id: int, allowed) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self.access.require(user, project.workspace_id, allowed, PROJECT_NOT_FOUND)
        return project

    @staticmethod
    def _ensure_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)

    async def create(self, user: User, workspace_id: int, payload: ProjectCreate) -> Project:
        await self._workspace_access(user, workspace_id, WRITE_ROLES)
        return await self.projects.create({"workspace_id": workspace_id, **payload.model_dump()})

    async def list_in_workspace(
        self, user: User, workspace_id: int, skip: int, limit: int
    ) -> tuple[list[Project], int]:
        await self._workspace_access(user, workspace_id, READ_ROLES)
        return (
            await self.projects.list_by_workspace(workspace_id, skip, limit),
            await self.projects.count_by_workspace(workspace_id),
        )

    async def get(self, user: User, project_id: int) -> Project:
        return await self._load(user, project_id, READ_ROLES)

    async def update(self, user: User, project_id: int, payload: ProjectUpdate) -> Project:
        project = await self._load(user, project_id, WRITE_ROLES)
        self._ensure_active(project)
        return await self.projects.update(project, payload.model_dump(exclude_unset=True))

    async def archive(self, user: User, project_id: int) -> Project:
        project = await self._load(user, project_id, WRITE_ROLES)
        if project.status == ProjectStatus.ARCHIVED:
            return project  # idempotent
        return await self.projects.update(project, {"status": ProjectStatus.ARCHIVED})

    async def delete(self, user: User, project_id: int) -> None:
        project = await self._load(user, project_id, MANAGE_ROLES)
        await self.projects.delete(project)
