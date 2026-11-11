import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_task_repo
from app.core.constants import TASK_NOT_FOUND
from app.main import app
from app.repositories.task_repository import TaskRepository

API = "/api/v1/tasks"


@pytest.fixture
def client():
    repo = TaskRepository()
    app.dependency_overrides[get_task_repo] = lambda: repo  # repo sạch cho mỗi test
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _create(client, title="Học FastAPI", **extra):
    r = client.post(API, json={"title": title, **extra})
    assert r.status_code == 201
    return r.json()


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_crud_flow(client):
    task = _create(client)
    assert task["status"] == "TODO" and task["priority"] == "MEDIUM"

    r = client.patch(f"{API}/{task['id']}", json={"status": "DONE"})
    assert r.json()["status"] == "DONE"
    assert r.json()["title"] == "Học FastAPI"  # exclude_unset: field khác giữ nguyên

    assert len(client.get(API).json()) == 1
    assert client.delete(f"{API}/{task['id']}").status_code == 204
    assert client.get(f"{API}/{task['id']}").status_code == 404


def test_validation_errors(client):
    from datetime import date, timedelta

    assert client.post(API, json={"title": ""}).status_code == 422
    past = (date.today() - timedelta(days=1)).isoformat()
    assert client.post(API, json={"title": "x", "due_date": past}).status_code == 422
    assert client.get(f"{API}?limit=1000").status_code == 422


# ---- Review #1: PATCH gửi null ----------------------------------------------
@pytest.mark.parametrize("body", [{"title": None}, {"status": None}, {"priority": None}])
def test_patch_rejects_explicit_null_on_required_fields(client, body):
    task = _create(client)
    assert client.patch(f"{API}/{task['id']}", json=body).status_code == 422
    # Dữ liệu không bị hỏng: GET chi tiết và GET danh sách vẫn 200
    assert client.get(f"{API}/{task['id']}").json()["title"] == "Học FastAPI"
    assert client.get(API).status_code == 200


def test_patch_allows_null_on_nullable_fields(client):
    task = _create(client, description="mô tả", due_date="2999-01-01")
    r = client.patch(f"{API}/{task['id']}", json={"description": None, "due_date": None})
    assert r.status_code == 200
    assert r.json()["description"] is None and r.json()["due_date"] is None


# ---- Review #2: exception nghiệp vụ + message dùng chung --------------------
def test_not_found_uses_shared_exception_and_message(client):
    for resp in (
        client.get(f"{API}/999"),
        client.patch(f"{API}/999", json={"title": "x"}),
        client.delete(f"{API}/999"),
    ):
        assert resp.status_code == 404
        assert resp.json() == {"detail": TASK_NOT_FOUND}


# ---- Review #3: chuỗi toàn khoảng trắng -------------------------------------
@pytest.mark.parametrize("title", ["", "   ", "\t\n"])
def test_blank_title_rejected_on_create_and_patch(client, title):
    assert client.post(API, json={"title": title}).status_code == 422
    task = _create(client)
    assert client.patch(f"{API}/{task['id']}", json={"title": title}).status_code == 422


def test_title_is_trimmed(client):
    assert _create(client, title="  Học FastAPI  ")["title"] == "Học FastAPI"


# ---- Review #4: service phải dùng repository được inject --------------------
def test_service_uses_injected_repository():
    class SpyRepo(TaskRepository):
        def __init__(self):
            super().__init__()
            self.calls: list[str] = []

        def create(self, data):
            self.calls.append("create")
            return super().create(data)

        def get(self, task_id):
            self.calls.append("get")
            return super().get(task_id)

    spy = SpyRepo()
    app.dependency_overrides[get_task_repo] = lambda: spy
    try:
        with TestClient(app) as c:
            task = _create(c)
            c.get(f"{API}/{task['id']}")
    finally:
        app.dependency_overrides.clear()
    assert spy.calls == ["create", "get"]
