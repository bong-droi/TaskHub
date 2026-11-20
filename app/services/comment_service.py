from app.core.constants import (
    COMMENT_NOT_FOUND,
    INSUFFICIENT_PERMISSION,
    PROJECT_ARCHIVED,
    TASK_NOT_FOUND,
)
from app.core.exceptions import ConflictException, ForbiddenException, NotFoundException
from app.core.permissions import READ_ROLES, WRITE_ROLES, can_delete_comment
from app.models import Comment, Project, Task, User
from app.models.enums import ProjectStatus, WorkspaceRole
from app.repositories.comment_repository import CommentRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.comment import CommentCreate
from app.services.access import AccessControl


class CommentService:
    def __init__(
        self,
        comments: CommentRepository,
        tasks: TaskRepository,
        projects: ProjectRepository,
        access: AccessControl,
    ) -> None:
        self.comments = comments
        self.tasks = tasks
        self.projects = projects
        self.access = access

    async def _task(self, user: User, task_id: int, allowed) -> tuple[Task, Project, WorkspaceRole]:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        project = await self.projects.get(task.project_id)
        role = await self.access.require(user, project.workspace_id, allowed, TASK_NOT_FOUND)
        return task, project, role

    async def add(self, user: User, task_id: int, payload: CommentCreate) -> Comment:
        task, project, _ = await self._task(user, task_id, WRITE_ROLES)
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)
        return await self.comments.create(
            {"task_id": task.id, "author_id": user.id, "content": payload.content}
        )

    async def list_for_task(
        self, user: User, task_id: int, skip: int, limit: int
    ) -> tuple[list[Comment], int]:
        await self._task(user, task_id, READ_ROLES)
        return (
            await self.comments.list_by_task(task_id, skip, limit),
            await self.comments.count_by_task(task_id),
        )

    async def delete(self, user: User, comment_id: int) -> None:
        comment = await self.comments.get(comment_id)
        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND)
        task = await self.tasks.get(comment.task_id)
        project = await self.projects.get(task.project_id)
        role = await self.access.require(user, project.workspace_id, READ_ROLES, COMMENT_NOT_FOUND)
        if not can_delete_comment(role, comment, user):
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        await self.comments.delete(comment)
