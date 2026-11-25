from fastapi import APIRouter, status

from app.api.deps import CommentServiceDep, CurrentUser, PaginationDep
from app.api.params import IdPath
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page

router = APIRouter(tags=["comments"])


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm comment (OWNER/EDITOR)",
)
async def add_comment(
    task_id: IdPath, payload: CommentCreate, user: CurrentUser, service: CommentServiceDep
):
    return await service.add(user, task_id, payload)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=Page[CommentRead],
    summary="Danh sách comment của task (cũ nhất trước)",
)
async def list_comments(
    task_id: IdPath, user: CurrentUser, service: CommentServiceDep, page: PaginationDep
):
    items, total = await service.list_for_task(user, task_id, page.skip, page.limit)
    return Page[CommentRead](items=items, total=total, page=page.page, limit=page.limit)


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá comment (tác giả hoặc OWNER)",
)
async def delete_comment(comment_id: IdPath, user: CurrentUser, service: CommentServiceDep):
    await service.delete(user, comment_id)
