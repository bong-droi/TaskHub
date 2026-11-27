"""Lấy resource + kiểm quyền + kiểm archive: MỘT chỗ duy nhất cho mọi service.

Trước đây mỗi service tự viết lại "lấy project/task, 404 nếu không có, kiểm quyền theo workspace,
kiểm project đã archive". Gom về đây để đổi một luật (vd thông báo lỗi, thứ tự kiểm tra, quy tắc
archive) chỉ phải sửa ở một nơi.

Quy ước chung của mọi hàm tải:
  - resource không tồn tại  -> 404 với message của resource đó
  - không phải thành viên workspace -> cũng 404, cùng message (không lộ resource có tồn tại)
  - là thành viên nhưng thiếu quyền -> 403
"""

from collections.abc import Collection
from dataclasses import dataclass

from app.core.constants import (
    COMMENT_NOT_FOUND,
    LABEL_NOT_FOUND,
    PROJECT_ARCHIVED,
    PROJECT_NOT_FOUND,
    TASK_NOT_FOUND,
    WORKSPACE_NOT_FOUND,
)
from app.core.exceptions import ConflictException, NotFoundException
from app.models import Comment, Label, Project, Task, User, Workspace
from app.models.enums import ProjectStatus, WorkspaceRole
from app.repositories.comment_repository import CommentRepository
from app.repositories.label_repository import LabelRepository
from app.repositories.project_repository import ProjectRepository
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.services.access import AccessControl


@dataclass(frozen=True)
class TaskContext:
    task: Task
    project: Project
    role: WorkspaceRole


@dataclass(frozen=True)
class LabelContext:
    label: Label
    project: Project
    role: WorkspaceRole


@dataclass(frozen=True)
class CommentContext:
    comment: Comment
    task: Task
    project: Project
    role: WorkspaceRole


class ResourceAccess:
    def __init__(
        self,
        access: AccessControl,
        workspaces: WorkspaceRepository,
        projects: ProjectRepository,
        tasks: TaskRepository,
        labels: LabelRepository,
        comments: CommentRepository,
    ) -> None:
        self.access = access
        self.workspaces = workspaces
        self.projects = projects
        self.tasks = tasks
        self.labels = labels
        self.comments = comments

    async def is_member(self, user_id: int, workspace_id: int) -> bool:
        return await self.access.is_member(user_id, workspace_id)

    # ------------------------------------------------------------------ loaders
    async def workspace(
        self, user: User, workspace_id: int, allowed: Collection[WorkspaceRole]
    ) -> Workspace:
        workspace = await self.workspaces.get(workspace_id)
        if workspace is None:
            raise NotFoundException(WORKSPACE_NOT_FOUND)
        await self.access.require(user, workspace.id, allowed, WORKSPACE_NOT_FOUND)
        return workspace

    async def project(
        self, user: User, project_id: int, allowed: Collection[WorkspaceRole]
    ) -> Project:
        project = await self.projects.get(project_id)
        if project is None:
            raise NotFoundException(PROJECT_NOT_FOUND)
        await self.access.require(user, project.workspace_id, allowed, PROJECT_NOT_FOUND)
        return project

    async def task(
        self, user: User, task_id: int, allowed: Collection[WorkspaceRole]
    ) -> TaskContext:
        task = await self.tasks.get(task_id)
        if task is None:
            raise NotFoundException(TASK_NOT_FOUND)
        project = await self.projects.get(task.project_id)
        role = await self.access.require(user, project.workspace_id, allowed, TASK_NOT_FOUND)
        return TaskContext(task, project, role)

    async def label(
        self, user: User, label_id: int, allowed: Collection[WorkspaceRole]
    ) -> LabelContext:
        label = await self.labels.get(label_id)
        if label is None:
            raise NotFoundException(LABEL_NOT_FOUND)
        project = await self.projects.get(label.project_id)
        role = await self.access.require(user, project.workspace_id, allowed, LABEL_NOT_FOUND)
        return LabelContext(label, project, role)

    async def comment(
        self, user: User, comment_id: int, allowed: Collection[WorkspaceRole]
    ) -> CommentContext:
        comment = await self.comments.get(comment_id)
        if comment is None:
            raise NotFoundException(COMMENT_NOT_FOUND)
        task = await self.tasks.get(comment.task_id)
        project = await self.projects.get(task.project_id)
        role = await self.access.require(user, project.workspace_id, allowed, COMMENT_NOT_FOUND)
        return CommentContext(comment, task, project, role)

    # ------------------------------------------------------------------ luật chung
    @staticmethod
    def ensure_active(project: Project) -> None:
        """Project đã archive là read-only: mọi thao tác GHI vào project/task/label/comment
        của nó đều phải gọi hàm này."""
        if project.status == ProjectStatus.ARCHIVED:
            raise ConflictException(PROJECT_ARCHIVED)
