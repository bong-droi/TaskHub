"""Tầng business logic (async). Chỉ raise exception nghiệp vụ, không biết gì về HTTP."""

from app.core.constants import (
    ASSIGNEE_NOT_FOUND,
    ASSIGNEE_NOT_IN_WORKSPACE,
    INSUFFICIENT_PERMISSION,
    LABEL_NOT_FOUND,
    LABEL_NOT_IN_PROJECT,
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
)
from app.core.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from app.core.permissions import READ_ROLES, WRITE_ROLES, can_delete_task
from app.models import Project, Task, User
from app.models.enums import ProjectStatus, TaskPriority, TaskStatus, UserRole, WorkspaceRole
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.user_repository import UserRepository
from app.schemas.task import TaskCreate, TaskCreateInProject, TaskUpdate
from app.services.access import AccessControl


class TaskService:
    def __init__(
        self,
        tasks: TaskRepository,
        projects: ProjectRepository,
        users: UserRepository,
        access: AccessControl,
        labels: LabelRepository,
    ) -> None:
        self.labels = labels
        self.tasks = tasks
        self.projects = projects
        self.users = users
        self.access = access

    async def list_tasks(self, user: User, skip: int, limit: int) -> tuple[list[Task], int]:
        if user.role == UserRole.ADMIN:
            return await self.tasks.list(skip, limit), await self.tasks.count()
        # Chỉ thấy task thuộc workspace mình là thành viên
        return (
            await self.tasks.list_visible(user.id, skip, limit),
            await self.tasks.count_visible(user.id),
        )

    async def _load(self, user: User, task_id: int, allowed) -> tuple[Task, Project, WorkspaceRole]:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)  # chỉ MỘT chỗ raise cho Task
        project = await self.projects.get(task.project_id)
        role = await self.access.require(user, project.workspace_id, allowed, TASK_NOT_FOUND)
        return task, project, role

    async def get_task(self, user: User, task_id: int) -> Task:
        task, _, _ = await self._load(user, task_id, READ_ROLES)
        return task

    async def _ensure_assignee(self, assignee_id: int | None, workspace_id: int) -> None:
        if assignee_id is None:
            return
        if await self.users.get(assignee_id) is None:
            raise NotFoundException(ASSIGNEE_NOT_FOUND)
        if not await self.access.is_member(assignee_id, workspace_id):
            raise BadRequestException(ASSIGNEE_NOT_IN_WORKSPACE)

    @staticmethod
    def _ensure_active(project: Project) -> None:
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)

    async def create_task(self, payload: TaskCreate, user: User) -> Task:
        project = await self.projects.get(payload.project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self.access.require(user, project.workspace_id, WRITE_ROLES, PROJECT_NOT_FOUND)
        self._ensure_active(project)
        await self._ensure_assignee(payload.assignee_id, project.workspace_id)
        return await self.tasks.create({**payload.model_dump(), "created_by": user.id})

    async def update_task(self, user: User, task_id: int, payload: TaskUpdate) -> Task:
        task, project, _ = await self._load(user, task_id, WRITE_ROLES)
        self._ensure_active(project)
        data = payload.model_dump(exclude_unset=True)
        await self._ensure_assignee(data.get("assignee_id"), project.workspace_id)
        return await self.tasks.update(task, data)

    async def delete_task(self, user: User, task_id: int) -> None:
        task, _, role = await self._load(user, task_id, READ_ROLES)
        if not can_delete_task(role, task, user):
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        await self.tasks.delete(task)

    # ---- task trong project: lọc + phân trang ----
    async def _project_for(self, user: User, project_id: int, allowed) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self.access.require(user, project.workspace_id, allowed, PROJECT_NOT_FOUND)
        return project

    async def list_in_project(
        self,
        user: User,
        project_id: int,
        skip: int,
        limit: int,
        *,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
        label_id: int | None = None,
    ) -> tuple[list[Task], int]:
        await self._project_for(user, project_id, READ_ROLES)
        filters = {
            "status": status,
            "priority": priority,
            "assignee_id": assignee_id,
            "label_id": label_id,
        }
        return (
            await self.tasks.list_by_project(project_id, skip, limit, **filters),
            await self.tasks.count_by_project(project_id, **filters),
        )

    async def create_in_project(
        self, user: User, project_id: int, payload: TaskCreateInProject
    ) -> Task:
        full = TaskCreate(project_id=project_id, **payload.model_dump())
        return await self.create_task(full, user)

    # ---- gắn / gỡ label ----
    async def _task_and_label(self, user: User, task_id: int, label_id: int):
        task, project, _ = await self._load(user, task_id, WRITE_ROLES)
        self._ensure_active(project)
        label = await self.labels.get(label_id)
        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND)
        if label.project_id != project.id:
            raise BadRequestException(LABEL_NOT_IN_PROJECT)
        return task, label

    async def add_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        return await self.tasks.add_label(task, label)

    async def remove_label(self, user: User, task_id: int, label_id: int) -> Task:
        task, label = await self._task_and_label(user, task_id, label_id)
        return await self.tasks.remove_label(task, label)
