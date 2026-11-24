from app.core.constants import INSUFFICIENT_PERMISSION
from app.core.exceptions import ForbiddenException
from app.core.permissions import READ_ROLES, WRITE_ROLES, can_delete_comment
from app.models import Comment, User
from app.repositories.comment_repository import CommentRepository
from app.schemas.comment import CommentCreate
from app.services.resource_access import ResourceAccess


class CommentService:
    def __init__(self, comments: CommentRepository, resources: ResourceAccess) -> None:
        self.comments = comments
        self.resources = resources

    async def add(self, user: User, task_id: int, payload: CommentCreate) -> Comment:
        ctx = await self.resources.task(user, task_id, WRITE_ROLES)
        self.resources.ensure_active(ctx.project)
        return await self.comments.create(
            {"task_id": ctx.task.id, "author_id": user.id, "content": payload.content}
        )

    async def list_for_task(
        self, user: User, task_id: int, skip: int, limit: int
    ) -> tuple[list[Comment], int]:
        await self.resources.task(user, task_id, READ_ROLES)
        return (
            await self.comments.list_by_task(task_id, skip, limit),
            await self.comments.count_by_task(task_id),
        )

    async def delete(self, user: User, comment_id: int) -> None:
        ctx = await self.resources.comment(user, comment_id, READ_ROLES)
        if not can_delete_comment(ctx.role, ctx.comment, user):
            raise ForbiddenException(INSUFFICIENT_PERMISSION)
        await self.comments.delete(ctx.comment)
