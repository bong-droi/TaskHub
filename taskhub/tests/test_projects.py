from app.core.constants import PROJECT_ARCHIVED, PROJECT_NOT_FOUND, WORKSPACE_NOT_FOUND
from tests.conftest import WS

PRJ = "/api/v1/projects"


def _list_url(team):
    return f"{WS}/{team.ws['id']}/projects"


async def test_create_requires_write_role(team, anon):
    url = _list_url(team)
    body = {"name": "  Mới  ", "description": "mô tả"}
    ok = await anon.post(url, json=body, headers=team.h["bob"])  # EDITOR
    assert ok.status_code == 201
    assert ok.json()["name"] == "Mới" and ok.json()["status"] == "ACTIVE"
    assert (await anon.post(url, json=body, headers=team.h["carol"])).status_code == 403  # VIEWER
    outsider = await anon.post(url, json=body, headers=team.h["dave"])
    assert outsider.status_code == 404 and outsider.json() == {"detail": WORKSPACE_NOT_FOUND}
    assert (await anon.post(url, json={"name": "  "}, headers=team.h["alice"])).status_code == 422


async def test_workspace_not_found(team, anon):
    r = await anon.post(f"{WS}/999/projects", json={"name": "x"}, headers=team.h["alice"])
    assert r.status_code == 404 and r.json() == {"detail": WORKSPACE_NOT_FOUND}


async def test_list_and_get_visible_to_all_members_only(team, anon):
    for who in ("alice", "bob", "carol"):
        page = (await anon.get(_list_url(team), headers=team.h[who])).json()
        assert page["total"] == 1 and page["items"][0]["name"] == "P"
        assert (
            await anon.get(f"{PRJ}/{team.project['id']}", headers=team.h[who])
        ).status_code == 200
    assert (await anon.get(_list_url(team), headers=team.h["dave"])).status_code == 404
    out = await anon.get(f"{PRJ}/{team.project['id']}", headers=team.h["dave"])
    assert out.status_code == 404 and out.json() == {"detail": PROJECT_NOT_FOUND}


async def test_pagination(team, anon):
    for i in range(3):
        await anon.post(_list_url(team), json={"name": f"P{i}"}, headers=team.h["alice"])
    page = (await anon.get(f"{_list_url(team)}?skip=1&limit=2", headers=team.h["alice"])).json()
    assert page["total"] == 4 and len(page["items"]) == 2


async def test_update_rules(team, anon):
    url = f"{PRJ}/{team.project['id']}"
    assert (await anon.patch(url, json={"name": "B"}, headers=team.h["bob"])).json()["name"] == "B"
    assert (await anon.patch(url, json={"name": "X"}, headers=team.h["carol"])).status_code == 403
    for bad in ({"name": None}, {"name": "   "}):
        assert (await anon.patch(url, json=bad, headers=team.h["bob"])).status_code == 422
    # null hợp lệ với description (nullable thật)
    r = await anon.patch(url, json={"description": None}, headers=team.h["bob"])
    assert r.status_code == 200 and r.json()["description"] is None
    # status không đổi được qua PATCH (phải qua /archive)
    r = await anon.patch(url, json={"status": "ARCHIVED"}, headers=team.h["bob"])
    assert r.json()["status"] == "ACTIVE"


async def test_archive_flow(team, anon):
    url = f"{PRJ}/{team.project['id']}"
    assert (await anon.post(f"{url}/archive", headers=team.h["carol"])).status_code == 403
    r = await anon.post(f"{url}/archive", headers=team.h["bob"])
    assert r.status_code == 200 and r.json()["status"] == "ARCHIVED"
    assert (
        await anon.post(f"{url}/archive", headers=team.h["bob"])
    ).status_code == 200  # idempotent
    locked = await anon.patch(url, json={"name": "X"}, headers=team.h["alice"])
    assert locked.status_code == 409 and locked.json() == {"detail": PROJECT_ARCHIVED}
    assert (await anon.get(url, headers=team.h["carol"])).status_code == 200  # vẫn xem được


async def test_only_owner_deletes_project_and_tasks_cascade(team, anon):
    url = f"{PRJ}/{team.project['id']}"
    task = await anon.post(
        "/api/v1/tasks",
        json={"title": "T", "project_id": team.project["id"]},
        headers=team.h["bob"],
    )
    assert task.status_code == 201
    assert (await anon.delete(url, headers=team.h["bob"])).status_code == 403
    assert (await anon.delete(url, headers=team.h["alice"])).status_code == 204
    assert (await anon.get(url, headers=team.h["alice"])).status_code == 404
    got = await anon.get(f"/api/v1/tasks/{task.json()['id']}", headers=team.h["alice"])
    assert got.status_code == 404
