from fastapi import APIRouter, status

from app.api.deps import CurrentUser, LabelServiceDep, PaginationDep
from app.api.params import IdPath
from app.api.responses import error_responses
from app.schemas.common import Page
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate

router = APIRouter(tags=["labels"])


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo label trong project (OWNER/EDITOR)",
    responses=error_responses(403, 404, 409),
)
async def create_label(
    project_id: IdPath, payload: LabelCreate, user: CurrentUser, service: LabelServiceDep
):
    return await service.create(user, project_id, payload)


@router.get(
    "/projects/{project_id}/labels",
    response_model=Page[LabelRead],
    summary="Danh sách label của project",
    responses=error_responses(404),
)
async def list_labels(
    project_id: IdPath, user: CurrentUser, service: LabelServiceDep, page: PaginationDep
):
    items, total = await service.list_in_project(user, project_id, page.skip, page.limit)
    return Page[LabelRead].create(
        items=[LabelRead.model_validate(item) for item in items],
        total=total,
        page=page.page,
        limit=page.limit,
    )


@router.patch(
    "/labels/{label_id}",
    response_model=LabelRead,
    summary="Sửa label (OWNER/EDITOR)",
    responses=error_responses(403, 404, 409),
)
async def update_label(
    label_id: IdPath, payload: LabelUpdate, user: CurrentUser, service: LabelServiceDep
):
    return await service.update(user, label_id, payload)


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá label, tự gỡ khỏi các task (OWNER/EDITOR)",
    responses=error_responses(403, 404),
)
async def delete_label(label_id: IdPath, user: CurrentUser, service: LabelServiceDep):
    await service.delete(user, label_id)
