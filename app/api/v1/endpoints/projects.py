from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, ProjectServiceDep
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(tags=["projects"])


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Tạo project (OWNER/EDITOR)",
)
async def create_project(
    workspace_id: int, payload: ProjectCreate, user: CurrentUser, service: ProjectServiceDep
):
    return await service.create(user, workspace_id, payload)


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=Page[ProjectRead],
    summary="Danh sách project trong workspace",
)
async def list_projects(
    workspace_id: int, user: CurrentUser, service: ProjectServiceDep, page: PaginationDep
):
    items, total = await service.list_in_workspace(user, workspace_id, page.skip, page.limit)
    return Page[ProjectRead](items=items, total=total, page=page.page, limit=page.limit)


@router.get("/projects/{project_id}", response_model=ProjectRead, summary="Chi tiết project")
async def get_project(project_id: int, user: CurrentUser, service: ProjectServiceDep):
    return await service.get(user, project_id)


@router.patch(
    "/projects/{project_id}", response_model=ProjectRead, summary="Sửa project (OWNER/EDITOR)"
)
async def update_project(
    project_id: int, payload: ProjectUpdate, user: CurrentUser, service: ProjectServiceDep
):
    return await service.update(user, project_id, payload)


@router.post(
    "/projects/{project_id}/archive",
    response_model=ProjectRead,
    summary="Archive project (OWNER/EDITOR)",
)
async def archive_project(project_id: int, user: CurrentUser, service: ProjectServiceDep):
    return await service.archive(user, project_id)


@router.delete(
    "/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá project (OWNER)",
)
async def delete_project(project_id: int, user: CurrentUser, service: ProjectServiceDep):
    await service.delete(user, project_id)
