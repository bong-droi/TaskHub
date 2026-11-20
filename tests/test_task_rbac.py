from app.core.constants import (
    ASSIGNEE_NOT_IN_WORKSPACE,
    INSUFFICIENT_PERMISSION,
    PROJECT_ARCHIVED,
    TASK_NOT_FOUND,
)

API = "/api/v1/tasks"


async def _task(anon, team, who="bob", **extra):
    r = await anon.post(
        API, json={"title": "T", "project_id": team.project["id"], **extra}, headers=team.h[who]
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_create_requires_write_role(team, anon):
    body = {"title": "T", "project_id": team.project["id"]}
    assert (await anon.post(API, json=body, headers=team.h["bob"])).status_code == 201
    assert (await anon.post(API, json=body, headers=team.h["alice"])).status_code == 201
    viewer = await anon.post(API, json=body, headers=team.h["carol"])
    assert viewer.status_code == 403 and viewer.json() == {"detail": INSUFFICIENT_PERMISSION}
    assert (await anon.post(API, json=body, headers=team.h["dave"])).status_code == 404


async def test_created_by_is_the_creator(team, anon):
    assert (await _task(anon, team, "bob"))["created_by"] == team.ids["bob"]


async def test_read_access_by_membership(team, anon):
    task = await _task(anon, team)
    url = f"{API}/{task['id']}"
    for who in ("alice", "bob", "carol"):
        assert (await anon.get(url, headers=team.h[who])).status_code == 200
    out = await anon.get(url, headers=team.h["dave"])
    assert out.status_code == 404 and out.json() == {
        "detail": TASK_NOT_FOUND
    }  # không lộ sự tồn tại


async def test_list_only_returns_visible_tasks(team, anon):
    await _task(anon, team)
    await _task(anon, team, "alice")
    assert (await anon.get(API, headers=team.h["carol"])).json()["total"] == 2
    dave = (await anon.get(API, headers=team.h["dave"])).json()
    assert dave["total"] == 0 and dave["items"] == []


async def test_update_requires_write_role(team, anon):
    url = f"{API}/{(await _task(anon, team))['id']}"
    assert (
        await anon.patch(url, json={"status": "DONE"}, headers=team.h["bob"])
    ).status_code == 200
    assert (
        await anon.patch(url, json={"status": "TODO"}, headers=team.h["carol"])
    ).status_code == 403
    assert (
        await anon.patch(url, json={"status": "TODO"}, headers=team.h["dave"])
    ).status_code == 404


async def test_delete_ownership_rules(team, anon):
    bobs = (await _task(anon, team, "bob"))["id"]
    alices = (await _task(anon, team, "alice"))["id"]
    # EDITOR chỉ xoá task của mình
    other = await anon.delete(f"{API}/{alices}", headers=team.h["bob"])
    assert other.status_code == 403 and other.json() == {"detail": INSUFFICIENT_PERMISSION}
    assert (await anon.delete(f"{API}/{bobs}", headers=team.h["bob"])).status_code == 204
    # VIEWER không xoá được, người ngoài không thấy
    assert (await anon.delete(f"{API}/{alices}", headers=team.h["carol"])).status_code == 403
    assert (await anon.delete(f"{API}/{alices}", headers=team.h["dave"])).status_code == 404
    # OWNER xoá được task của người khác
    bobs2 = (await _task(anon, team, "bob"))["id"]
    assert (await anon.delete(f"{API}/{bobs2}", headers=team.h["alice"])).status_code == 204


async def test_assignee_must_belong_to_workspace(team, anon):
    ok = await _task(anon, team, assignee_id=team.ids["carol"])
    assert ok["assignee_id"] == team.ids["carol"]
    bad = await anon.post(
        API,
        json={"title": "T", "project_id": team.project["id"], "assignee_id": team.ids["dave"]},
        headers=team.h["bob"],
    )
    assert bad.status_code == 400 and bad.json() == {"detail": ASSIGNEE_NOT_IN_WORKSPACE}
    upd = await anon.patch(
        f"{API}/{ok['id']}", json={"assignee_id": team.ids["dave"]}, headers=team.h["bob"]
    )
    assert upd.status_code == 400
    unassign = await anon.patch(
        f"{API}/{ok['id']}", json={"assignee_id": None}, headers=team.h["bob"]
    )
    assert unassign.status_code == 200 and unassign.json()["assignee_id"] is None


async def test_archived_project_is_read_only_for_tasks(team, anon):
    task = await _task(anon, team)
    await anon.post(f"/api/v1/projects/{team.project['id']}/archive", headers=team.h["alice"])
    body = {"title": "N", "project_id": team.project["id"]}
    create = await anon.post(API, json=body, headers=team.h["alice"])
    assert create.status_code == 409 and create.json() == {"detail": PROJECT_ARCHIVED}
    update = await anon.patch(f"{API}/{task['id']}", json={"title": "x"}, headers=team.h["alice"])
    assert update.status_code == 409
    assert (await anon.get(f"{API}/{task['id']}", headers=team.h["carol"])).status_code == 200
    assert (await anon.delete(f"{API}/{task['id']}", headers=team.h["alice"])).status_code == 204


async def test_removed_member_loses_task_access(team, anon):
    task = await _task(anon, team)
    await anon.delete(
        f"/api/v1/workspaces/{team.ws['id']}/members/{team.ids['bob']}", headers=team.h["alice"]
    )
    assert (await anon.get(f"{API}/{task['id']}", headers=team.h["bob"])).status_code == 404
