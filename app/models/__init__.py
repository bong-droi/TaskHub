"""Import tất cả model để Base.metadata (và Alembic) nhìn thấy đủ bảng."""
from app.models.comment import Comment
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task, task_labels
from app.models.user import User
from app.models.workspace import Workspace, WorkspaceMember

__all__ = [
    "Comment", "Label", "Project", "Task", "task_labels",
    "User", "Workspace", "WorkspaceMember",
]
