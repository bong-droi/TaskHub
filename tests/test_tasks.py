from datetime import date, timedelta

import pytest

from app.core.constants import ASSIGNEE_NOT_FOUND, PROJECT_NOT_FOUND, TASK_NOT_FOUND

API = "/api/v1/tasks"


async def test_health(client):
    assert (await client.get("/api/v1/health")).json() == {"status": "ok"}


async def test_crud_flow(client, seeded):
    r = await client.post(API, json={"title": "Học SQLAlchemy", "project_id": seeded["project_id"]})
    assert r.status_code == 201
    task = r.json()
    assert task["status"] == "TODO" and task["priority"] == "MEDIUM"
    assert task["created_at"]  # server_default đã được nạp lại

    r = await client.patch(f"{API}/{task['id']}", json={"status": "DONE"})
    assert r.json()["status"] == "DONE"
    assert r.json()["title"] == "Học SQLAlchemy"  # exclude_unset: field khác giữ nguyên

    assert (await client.get(f"{API}/{task['id']}")).status_code == 200
    assert (await client.delete(f"{API}/{task['id']}")).status_code == 204
    assert (await client.get(f"{API}/{task['id']}")).status_code == 404


async def test_pagination(client, seeded):
    for i in range(5):
        await client.post(API, json={"title": f"T{i}", "project_id": seeded["project_id"]})
    page = (await client.get(f"{API}?skip=1&limit=2")).json()
    assert page["total"] == 5 and len(page["items"]) == 2
    assert [t["title"] for t in page["items"]] == ["T1", "T2"]


async def test_assign_user(client, seeded):
    body = {"title": "A", "project_id": seeded["project_id"], "assignee_id": seeded["user_id"]}
    assert (await client.post(API, json=body)).json()["assignee_id"] == seeded["user_id"]
    body["assignee_id"] = 9999
    assert (await client.post(API, json=body)).status_code == 404


async def test_foreign_key_checks(client):
    assert (await client.post(API, json={"title": "x", "project_id": 9999})).status_code == 404


async def test_validation_errors(client, seeded):
    pid = seeded["project_id"]
    assert (await client.post(API, json={"title": "", "project_id": pid})).status_code == 422
    past = (date.today() - timedelta(days=1)).isoformat()
    r = await client.post(API, json={"title": "x", "project_id": pid, "due_date": past})
    assert r.status_code == 422
    assert (await client.get(f"{API}?limit=1000")).status_code == 422


# ---- Review: PATCH gửi null ---------------------------------------------------
async def _new_task(client, seeded, **extra):
    r = await client.post(API, json={"title": "Học", "project_id": seeded["project_id"], **extra})
    assert r.status_code == 201
    return r.json()


@pytest.mark.parametrize("body", [{"title": None}, {"status": None}, {"priority": None}])
async def test_patch_rejects_explicit_null_on_required_fields(client, seeded, body):
    task = await _new_task(client, seeded)
    assert (await client.patch(f"{API}/{task['id']}", json=body)).status_code == 422
    # Dữ liệu không bị hỏng: GET chi tiết và GET danh sách vẫn 200
    assert (await client.get(f"{API}/{task['id']}")).json()["title"] == "Học"
    assert (await client.get(API)).status_code == 200


async def test_patch_allows_null_on_nullable_fields(client, seeded):
    task = await _new_task(
        client,
        seeded,
        description="mô tả",
        due_date="2999-01-01",
        assignee_id=seeded["user_id"],
    )
    r = await client.patch(
        f"{API}/{task['id']}", json={"description": None, "due_date": None, "assignee_id": None}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["description"] is None and body["due_date"] is None
    assert body["assignee_id"] is None  # null = bỏ gán


# ---- Review: NotFoundException + message dùng chung ---------------------------
async def test_not_found_uses_shared_messages(client, seeded):
    for resp in (
        await client.get(f"{API}/999"),
        await client.patch(f"{API}/999", json={"title": "x"}),
        await client.delete(f"{API}/999"),
    ):
        assert resp.status_code == 404
        assert resp.json() == {"detail": TASK_NOT_FOUND}
    r = await client.post(API, json={"title": "x", "project_id": 9999})
    assert r.json() == {"detail": PROJECT_NOT_FOUND}
    r = await client.post(
        API, json={"title": "x", "project_id": seeded["project_id"], "assignee_id": 9999}
    )
    assert r.json() == {"detail": ASSIGNEE_NOT_FOUND}


# ---- Review: chuỗi toàn khoảng trắng -----------------------------------------
@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
async def test_blank_title_rejected_on_create_and_patch(client, seeded, title):
    pid = seeded["project_id"]
    assert (await client.post(API, json={"title": title, "project_id": pid})).status_code == 422
    task = await _new_task(client, seeded)
    assert (await client.patch(f"{API}/{task['id']}", json={"title": title})).status_code == 422


async def test_title_is_trimmed(client, seeded):
    assert (await _new_task(client, seeded, title="  Học FastAPI  "))["title"] == "Học FastAPI"


async def test_created_by_is_current_user(client, seeded):
    r = await client.post(API, json={"title": "Của tôi", "project_id": seeded["project_id"]})
    assert r.json()["created_by"] == seeded["user_id"]


async def test_tasks_require_login(anon, seeded):
    r = await anon.post(API, json={"title": "x", "project_id": seeded["project_id"]})
    assert r.status_code == 401
