from datetime import date, timedelta

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
