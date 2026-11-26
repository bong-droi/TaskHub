"""Session 8: Kiểm thử End-to-End (E2E) luồng nghiệp vụ & chất lượng kiến trúc (DRY/Async)."""

from app.core import constants
from app.core.security import hash_password_async, verify_password_async
from app.models import Project, User, Workspace
from app.repositories.task_repository import TaskRepository
from app.repositories.workspace_repository import WorkspaceRepository
from app.schemas.base import BaseSchema, not_nullable, reject_explicit_nulls
from app.schemas.common import Page, PaginatedResponse


async def test_e2e_full_business_workflow(anon, redis_cache, outbox) -> None:
    """Luồng nghiệp vụ khép kín từ đầu đến cuối:
    Register/Login -> Tạo Workspace -> Mời thành viên -> Tạo Project -> Tạo & Gắn Label
    -> Tạo Task & Gửi Background Email -> Thêm/Xóa Comment -> Archive Project -> Xóa Task (204).
    """
    # 1. Register Owner & Member
    owner_reg = await anon.post(
        "/api/v1/auth/register",
        json={
            "email": "  Owner.E2E@TaskHub.dev ",
            "password": "OwnerPassword123!",
            "full_name": "  Owner E2E  ",
        },
    )
    assert owner_reg.status_code == 201
    owner_data = owner_reg.json()
    assert owner_data["email"] == "owner.e2e@taskhub.dev"
    assert owner_data["full_name"] == "Owner E2E"

    member_reg = await anon.post(
        "/api/v1/auth/register",
        json={
            "email": "member.e2e@taskhub.dev",
            "password": "MemberPassword123!",
            "full_name": "Member E2E",
        },
    )
    assert member_reg.status_code == 201
    member_id = member_reg.json()["id"]

    # Login lấy JWT access_token
    login_resp = await anon.post(
        "/api/v1/auth/login",
        data={"username": "owner.e2e@taskhub.dev", "password": "OwnerPassword123!"},
    )
    assert login_resp.status_code == 200
    owner_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}

    # 2. Tạo Workspace (Unit-of-Work: tạo Workspace + WorkspaceMember OWNER)
    ws_resp = await anon.post(
        "/api/v1/workspaces",
        json={"name": "  E2E Production Workspace  "},
        headers=owner_headers,
    )
    assert ws_resp.status_code == 201
    ws = ws_resp.json()
    assert ws["name"] == "E2E Production Workspace"
    ws_id = ws["id"]

    # Mời thành viên EDITOR vào Workspace
    invite_resp = await anon.post(
        f"/api/v1/workspaces/{ws_id}/members",
        json={"email": "member.e2e@taskhub.dev", "role": "EDITOR"},
        headers=owner_headers,
    )
    assert invite_resp.status_code == 201

    # 3. Tạo Project
    proj_resp = await anon.post(
        f"/api/v1/workspaces/{ws_id}/projects",
        json={"name": "  Release v1.0  ", "description": "E2E test project"},
        headers=owner_headers,
    )
    assert proj_resp.status_code == 201
    project = proj_resp.json()
    assert project["name"] == "Release v1.0"
    project_id = project["id"]

    # 4. Tạo Label trong Project
    label_resp = await anon.post(
        f"/api/v1/projects/{project_id}/labels",
        json={"name": "  Backend  ", "color": "#FF5733"},
        headers=owner_headers,
    )
    assert label_resp.status_code == 201
    label = label_resp.json()
    assert label["name"] == "Backend"
    label_id = label["id"]

    # 5. Tạo Task & Gửi Background Email khi giao cho thành viên khác
    task_resp = await anon.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={
            "title": "  Hoàn thiện Docker & E2E  ",
            "description": "Đóng gói multi-stage và kiểm thử",
            "priority": "HIGH",
            "assignee_id": member_id,
        },
        headers=owner_headers,
    )
    assert task_resp.status_code == 201
    task = task_resp.json()
    task_id = task["id"]
    assert task["title"] == "Hoàn thiện Docker & E2E"
    assert task["assignee_id"] == member_id
    assert len(outbox.sent) == 1
    assert outbox.sent[0].to == "member.e2e@taskhub.dev"
    assert "Hoàn thiện Docker & E2E" in outbox.sent[0].subject

    # Gắn Label vào Task
    attach_resp = await anon.post(
        f"/api/v1/tasks/{task_id}/labels/{label_id}",
        headers=owner_headers,
    )
    assert attach_resp.status_code == 200
    assert [lb["name"] for lb in attach_resp.json()["labels"]] == ["Backend"]

    # Kiểm tra danh sách Task trong Project + Redis Cache (MISS -> HIT)
    list_miss = await anon.get(
        f"/api/v1/projects/{project_id}/tasks?priority=HIGH",
        headers=owner_headers,
    )
    assert list_miss.status_code == 200
    assert list_miss.headers["X-Cache"] == "MISS"
    assert list_miss.json()["total"] == 1

    list_hit = await anon.get(
        f"/api/v1/projects/{project_id}/tasks?priority=HIGH",
        headers=owner_headers,
    )
    assert list_hit.status_code == 200
    assert list_hit.headers["X-Cache"] == "HIT"

    # 6. Thêm & Xóa Comment trên Task
    comment_resp = await anon.post(
        f"/api/v1/tasks/{task_id}/comments",
        json={"content": "  Đã kiểm tra xong toàn bộ luồng!  "},
        headers=owner_headers,
    )
    assert comment_resp.status_code == 201
    comment = comment_resp.json()
    assert comment["content"] == "Đã kiểm tra xong toàn bộ luồng!"
    comment_id = comment["id"]

    comments_list = await anon.get(
        f"/api/v1/tasks/{task_id}/comments",
        headers=owner_headers,
    )
    assert comments_list.status_code == 200
    assert comments_list.json()["total"] == 1

    del_comment_resp = await anon.delete(
        f"/api/v1/comments/{comment_id}",
        headers=owner_headers,
    )
    assert del_comment_resp.status_code == 204

    # 7. Archive Project -> Chặn thao tác ghi mới (409 Conflict)
    archive_resp = await anon.post(
        f"/api/v1/projects/{project_id}/archive",
        headers=owner_headers,
    )
    assert archive_resp.status_code == 200
    assert archive_resp.json()["status"] == "ARCHIVED"

    blocked_task = await anon.post(
        f"/api/v1/projects/{project_id}/tasks",
        json={"title": "Task sau khi archive"},
        headers=owner_headers,
    )
    assert blocked_task.status_code == 409

    # 8. Xóa Task (204 No Content)
    del_task_resp = await anon.delete(
        f"/api/v1/tasks/{task_id}",
        headers=owner_headers,
    )
    assert del_task_resp.status_code == 204

    get_deleted = await anon.get(
        f"/api/v1/tasks/{task_id}",
        headers=owner_headers,
    )
    assert get_deleted.status_code == 404


async def test_session8_dry_and_async_optimizations(session_factory, seeded) -> None:
    """Kiểm tra Refactor DRY, PaginatedResponse.create, Non-blocking bcrypt & ORM loading."""
    # 1. Constants tập trung tại app/core/constants.py
    assert constants.TITLE_MIN_LENGTH == 1
    assert constants.TITLE_MAX_LENGTH == 200
    assert constants.PASSWORD_MAX_LENGTH == 72
    assert constants.MAX_LIMIT == 100
    assert constants.MEMORY_CACHE_MAX_KEYS > 0

    # 2. BaseSchema & reject_explicit_nulls / not_nullable
    assert reject_explicit_nulls is not_nullable
    assert BaseSchema.model_config.get("str_strip_whitespace") is True

    # 3. PaginatedResponse.create() / Page.create()
    page = PaginatedResponse[int].create(items=[1, 2, 3], total=25, page=1, limit=10)
    assert isinstance(page, Page)
    assert page.total == 25 and page.pages == 3 and page.items == [1, 2, 3]

    # 4. Non-blocking async bcrypt (asyncio.to_thread)
    hashed = await hash_password_async("AsyncSecret123!")
    assert await verify_password_async("AsyncSecret123!", hashed) is True
    assert await verify_password_async("WrongPassword", hashed) is False

    # 5. SQLAlchemy relationships: User/Workspace/Project không bật lazy="selectin" tràn lan
    for model in (User, Workspace, Project):
        for rel in model.__mapper__.relationships:
            assert rel.lazy != "selectin", (
                f"{model.__name__}.{rel.key} không được dùng lazy='selectin'"
            )

    # 6. get_by_id_with_details nạp chi tiết bằng selectinload tường minh
    async with session_factory() as db:
        ws_repo = WorkspaceRepository(db)
        ws = await ws_repo.create_with_owner("UoW Workspace", seeded["user_id"])
        ws_detail = await ws_repo.get_by_id_with_details(ws.id)
        assert ws_detail is not None and len(ws_detail.members) == 1

        task_repo = TaskRepository(db)
        created_task = await task_repo.create(
            {
                "title": "Detail Task",
                "project_id": seeded["project_id"],
                "created_by": seeded["user_id"],
            }
        )
        detail = await task_repo.get_by_id_with_details(created_task.id)
        assert detail is not None and detail.id == created_task.id
        assert isinstance(detail.labels, list) and isinstance(detail.comments, list)
