from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, WorkspaceServiceDep
from app.api.params import IdPath
from app.api.responses import error_responses
from app.schemas.common import Page
from app.schemas.workspace import (
    MemberInvite,
    MemberRead,
    MemberRoleUpdate,
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
    return Page[WorkspaceRead].create(
        items=[WorkspaceRead.model_validate(item) for item in items],
        total=total,
        page=page.page,
        limit=page.limit,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Chi tiết workspace",
    responses=error_responses(404),
)
async def get_workspace(workspace_id: IdPath, user: CurrentUser, service: WorkspaceServiceDep):
    return await service.get(user, workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceRead,
    summary="Sửa workspace (OWNER)",
    responses=error_responses(403, 404),
)
async def update_workspace(
    workspace_id: IdPath, payload: WorkspaceUpdate, user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.update(user, workspace_id, payload)


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá workspace (OWNER)",
    responses=error_responses(403, 404),
)
async def delete_workspace(workspace_id: IdPath, user: CurrentUser, service: WorkspaceServiceDep):
    await service.delete(user, workspace_id)


@router.post(
    "/{workspace_id}/members",
    response_model=MemberRead,
    status_code=status.HTTP_201_CREATED,
    summary="Mời thành viên (OWNER)",
    responses=error_responses(403, 404, 409),
)
async def invite_member(
    workspace_id: IdPath, payload: MemberInvite, user: CurrentUser, service: WorkspaceServiceDep
):
    return await service.invite_member(user, workspace_id, payload)


@router.get(
    "/{workspace_id}/members",
    response_model=list[MemberRead],
    summary="Danh sách thành viên",
    responses=error_responses(404),
)
async def list_members(workspace_id: IdPath, user: CurrentUser, service: WorkspaceServiceDep):
    return await service.list_members(user, workspace_id)


@router.patch(
    "/{workspace_id}/members/{user_id}",
    response_model=MemberRead,
    summary="Đổi vai trò thành viên (OWNER)",
    responses=error_responses(400, 403, 404),
)
async def update_member_role(
    workspace_id: IdPath,
    user_id: IdPath,
    payload: MemberRoleUpdate,
    user: CurrentUser,
    service: WorkspaceServiceDep,
):
    return await service.update_member_role(user, workspace_id, user_id, payload)


@router.delete(
    "/{workspace_id}/members/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xoá thành viên (OWNER)",
    responses=error_responses(400, 403, 404),
)
async def remove_member(
    workspace_id: IdPath, user_id: IdPath, user: CurrentUser, service: WorkspaceServiceDep
):
    await service.remove_member(user, workspace_id, user_id)
