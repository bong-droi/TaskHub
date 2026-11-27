"""Gửi thông báo qua email bằng BackgroundTasks: response trả về trước, email gửi sau."""

import logging

from fastapi import BackgroundTasks

from app.core.email import Email, EmailBackend
from app.models import Project, Task, User

logger = logging.getLogger("taskhub.notifier")


def build_assignment_email(
    task: Task, project: Project, assignee: User, assigned_by: User
) -> Email:
    due = task.due_date.isoformat() if task.due_date else "chưa đặt"
    body = (
        f"Xin chào {assignee.full_name},\n\n"
        f'{assigned_by.full_name} vừa giao cho bạn một task trong project "{project.name}":\n\n'
        f"  Tiêu đề : {task.title}\n"
        f"  Ưu tiên : {task.priority.value}\n"
        f"  Hạn     : {due}\n"
        f"  Mã task : #{task.id}\n\n"
        "TaskHub"
    )
    return Email(
        to=assignee.email,
        subject=f"[TaskHub] Bạn được giao task: {task.title}",
        body=body,
        task_id=task.id,
        recipient_user_id=assignee.id,
    )


class Notifier:
    def __init__(self, background: BackgroundTasks, backend: EmailBackend) -> None:
        self.background = background
        self.backend = backend

    def task_assigned(
        self, task: Task, project: Project, assignee: User, assigned_by: User
    ) -> None:
        if assignee.id == assigned_by.id:
            return  # tự giao cho mình thì không cần báo
        # Dựng nội dung NGAY (khi object còn hợp lệ), chỉ việc gửi là chạy nền
        message = build_assignment_email(task, project, assignee, assigned_by)
        self.background.add_task(self._send_safely, message)

    async def _send_safely(self, message: Email) -> None:
        """Lỗi gửi email chỉ được ghi log: response đã trả về, không được làm hỏng gì."""
        try:
            await self.backend.send(message)
        except Exception:
            logger.exception(
                "Gửi email thất bại: user_id=%s task_id=%s subject=%s",
                message.recipient_user_id,
                message.task_id,
                message.subject,
            )
