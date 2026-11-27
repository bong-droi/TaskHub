from fastapi import APIRouter, status

from app.api.deps import CommentServiceDep, CurrentUser, PaginationDep
from app.api.params import IdPath
from app.api.responses import error_responses
from app.schemas.comment import CommentCreate, CommentRead
from app.schemas.common import Page

router = APIRouter(tags=["comments"])


@router.post(
    "/tasks/{task_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Thêm comment (OWNER/EDITOR)",
    responses=error_responses(403, 404, 409),
)
async def add_comment(
    task_id: IdPath, payload: CommentCreate, user: CurrentUser, service: CommentServiceDep
):
    return await service.add(user, task_id, payload)


@router.get(
    "/tasks/{task_id}/comments",
    response_model=Page[CommentRead],
    summary="Danh sách comment của task (cũ nhất trước)",
    responses=error_responses(404),
)
async def list_comments(
    task_id: IdPath, user: CurrentUser, service: CommentServiceDep, page: PaginationDep
):
    items, total = await service.list_for_task(user, task_id, page.skip, page.limit)
    return Page[CommentRead].create(
        items=[CommentRead.model_validate(item) for item in items],
        total=total,
        page=page.page,
        limit=page.limit,
    )


@router.delete(
    "/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá comment (tác giả hoặc OWNER)",
    responses=error_responses(403, 404),
)
async def delete_comment(comment_id: IdPath, user: CurrentUser, service: CommentServiceDep):
    await service.delete(user, comment_id)
