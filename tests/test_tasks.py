from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_task_repo
from app.main import app
from app.repositories.task_repository import TaskRepository


@pytest.fixture
def client():
    repo = TaskRepository()
    app.dependency_overrides[get_task_repo] = lambda: repo  # repo sạch cho mỗi test
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get("/api/v1/health").json() == {"status": "ok"}


def test_crud_flow(client):
    r = client.post("/api/v1/tasks", json={"title": "Học FastAPI"})
    assert r.status_code == 201
    task = r.json()
    assert task["status"] == "TODO" and task["priority"] == "MEDIUM"

    r = client.patch(f"/api/v1/tasks/{task['id']}", json={"status": "DONE"})
    assert r.json()["status"] == "DONE"
    assert r.json()["title"] == "Học FastAPI"  # exclude_unset: field khác giữ nguyên

    assert len(client.get("/api/v1/tasks").json()) == 1
    assert client.delete(f"/api/v1/tasks/{task['id']}").status_code == 204
    assert client.get(f"/api/v1/tasks/{task['id']}").status_code == 404


def test_validation_errors(client):
    assert client.post("/api/v1/tasks", json={"title": ""}).status_code == 422
    past = (date.today() - timedelta(days=1)).isoformat()
    r = client.post("/api/v1/tasks", json={"title": "x", "due_date": past})
    assert r.status_code == 422
    assert client.get("/api/v1/tasks?limit=1000").status_code == 422
