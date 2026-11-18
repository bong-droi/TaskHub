from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, WorkspaceServiceDep
from app.schemas.common import Page
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    WorkspaceCreate,
    WorkspaceRead,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post(
    "", response_model=WorkspaceRead, status_code=status.HTTP_201_CREATED, summary="Tạo workspace"
)
async def create_workspace(
    payload: WorkspaceCreate, user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.create(user, payload)


@router.get("", response_model=Page[WorkspaceRead], summary="Workspace của tôi")
async def list_workspaces(user: CurrentUser, service: WorkspaceServiceDep, page: PaginationDep):
    items, total = await service.list_for(user, page.skip, page.limit)
    return Page[WorkspaceRead](items=items, total=total, skip=page.skip, limit=page.limit)


@router.get("/{workspace_id}", response_model=WorkspaceRead, summary="Chi tiết workspace")
async def get_workspace(workspace_id: int, user: CurrentUser, service: WorkspaceServiceDep):
    return await service.get(user, workspace_id)


@router.patch("/{workspace_id}", response_model=WorkspaceRead, summary="Sửa workspace (OWNER)")
async def update_workspace(
    workspace_id: int, payload: WorkspaceUpdate, user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.update(user, workspace_id, payload)


@router.delete(
    "/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xoá workspace (OWNER)"
)
async def delete_workspace(workspace_id: int, user: CurrentUser, service: WorkspaceServiceDep):
    await service.delete(user, workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Mời thành viên (OWNER)",
)
async def invite_member(
    workspace_id: int, payload: MemberInvite, user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.invite_member(user, workspace_id, payload)


@router.get(
    "/{workspace_id}/members", response_model=list[MemberRead], summary="Danh sách thành viên"
)
async def list_members(workspace_id: int, user: CurrentUser, service: WorkspaceServiceDep):
    return await service.list_members(user, workspace_id)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá thành viên (OWNER)",
)
async def remove_member(
    workspace_id: int, user_id: int, user: CurrentUser, service: WorkspaceServiceDep
):
    await service.remove_member(user, workspace_id, user_id)
