from fastapi import APIRouter, status

from app.api.deps import CurrentUser, LabelServiceDep, PaginationDep
from app.schemas.common import Page
from app.schemas.label import LabelCreate, LabelRead, LabelUpdate

router = APIRouter(tags=["labels"])


@router.post(
    "/projects/{project_id}/labels",
    response_model=LabelRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo label trong project (OWNER/EDITOR)",
)
async def create_label(
    project_id: int, payload: LabelCreate, user: CurrentUser, service: LabelServiceDep
):
    return await service.create(user, project_id, payload)


@router.get(
    "/projects/{project_id}/labels",
    response_model=Page[LabelRead],
    summary="Danh sách label của project",
)
async def list_labels(
    project_id: int, user: CurrentUser, service: LabelServiceDep, page: PaginationDep
):
    items, total = await service.list_in_project(user, project_id, page.skip, page.limit)
    return Page[LabelRead](items=items, total=total, page=page.page, limit=page.limit)


@router.patch("/labels/{label_id}", response_model=LabelRead, summary="Sửa label (OWNER/EDITOR)")
async def update_label(
    label_id: int, payload: LabelUpdate, user: CurrentUser, service: LabelServiceDep
):
    return await service.update(user, label_id, payload)


@router.delete(
    "/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá label, tự gỡ khỏi các task (OWNER/EDITOR)",
)
async def delete_label(label_id: int, user: CurrentUser, service: LabelServiceDep):
    await service.delete(user, label_id)
