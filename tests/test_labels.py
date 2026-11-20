from app.core.constants import (
    LABEL_NAME_EXISTS,
    LABEL_NOT_FOUND,
    LABEL_NOT_IN_PROJECT,
    PROJECT_ARCHIVED,
)

PRJ = "/api/v1/projects"
TASKS = "/api/v1/tasks"
LABELS = "/api/v1/labels"


def _labels_url(team):
    return f"{PRJ}/{team.project['id']}/labels"


async def _label(anon, team, name="bug", who="alice", **extra):
    r = await anon.post(_labels_url(team), json={"name": name, **extra}, headers=team.h[who])
    assert r.status_code == 201, r.text
    return r.json()


async def _task(anon, team, who="alice"):
    r = await anon.post(
        f"{PRJ}/{team.project['id']}/tasks", json={"title": "T"}, headers=team.h[who]
    )
    return r.json()


async def _other_project(anon, team):
    r = await anon.post(
        f"/api/v1/workspaces/{team.ws['id']}/projects",
        json={"name": "Other"},
        headers=team.h["alice"],
    )
    return r.json()


# ------------------------------------------------------------------ CRUD
async def test_create_label_rules(team, anon):
    body = {"name": "  bug  ", "color": "#FF5733"}
    ok = await anon.post(_labels_url(team), json=body, headers=team.h["bob"])  # EDITOR
    assert ok.status_code == 201
    assert ok.json()["name"] == "bug" and ok.json()["color"] == "#FF5733"
    assert ok.json()["project_id"] == team.project["id"]
    assert (
        await anon.post(_labels_url(team), json=body, headers=team.h["carol"])
    ).status_code == 403
    assert (
        await anon.post(_labels_url(team), json=body, headers=team.h["dave"])
    ).status_code == 404


async def test_default_color_and_validation(team, anon):
    assert (await _label(anon, team, "feature"))["color"] == "#808080"
    h = team.h["alice"]
    for bad in ({"name": "   "}, {"name": ""}, {"name": "x" * 51}):
        assert (await anon.post(_labels_url(team), json=bad, headers=h)).status_code == 422
    for color in ("red", "#FFF", "#GGGGGG", "FF5733", "#FF57331"):
        r = await anon.post(_labels_url(team), json={"name": "c", "color": color}, headers=h)
        assert r.status_code == 422, color


async def test_name_is_unique_per_project_case_insensitive(team, anon):
    await _label(anon, team, "Bug")
    dup = await anon.post(_labels_url(team), json={"name": "bug"}, headers=team.h["alice"])
    assert dup.status_code == 409 and dup.json() == {"detail": LABEL_NAME_EXISTS}
    other = await _other_project(anon, team)  # cùng tên ở project khác thì hợp lệ
    r = await anon.post(
        f"{PRJ}/{other['id']}/labels", json={"name": "Bug"}, headers=team.h["alice"]
    )
    assert r.status_code == 201


async def test_list_labels_paginated_for_members_only(team, anon):
    for name in ("a", "b", "c"):
        await _label(anon, team, name)
    page = (await anon.get(f"{_labels_url(team)}?page=2&limit=2", headers=team.h["carol"])).json()
    assert page["total"] == 3 and page["pages"] == 2 and [i["name"] for i in page["items"]] == ["c"]
    assert (await anon.get(_labels_url(team), headers=team.h["dave"])).status_code == 404
    assert (await anon.get(f"{PRJ}/999/labels", headers=team.h["alice"])).status_code == 404


async def test_update_label(team, anon):
    a, b = await _label(anon, team, "a"), await _label(anon, team, "b")
    h = team.h["bob"]
    r = await anon.patch(f"{LABELS}/{a['id']}", json={"name": "A2", "color": "#00FF00"}, headers=h)
    assert r.status_code == 200 and r.json()["name"] == "A2" and r.json()["color"] == "#00FF00"
    # đổi sang tên đã có -> 409; giữ nguyên tên của chính nó -> hợp lệ
    clash = await anon.patch(f"{LABELS}/{a['id']}", json={"name": "B"}, headers=h)
    assert clash.status_code == 409
    same = await anon.patch(f"{LABELS}/{b['id']}", json={"name": "b"}, headers=h)
    assert same.status_code == 200
    # review #1: null không được ghi đè field NOT NULL
    for bad in ({"name": None}, {"color": None}, {"color": "blue"}):
        assert (await anon.patch(f"{LABELS}/{a['id']}", json=bad, headers=h)).status_code == 422
    assert (
        await anon.patch(f"{LABELS}/{a['id']}", json={"name": "x"}, headers=team.h["carol"])
    ).status_code == 403
    assert (
        await anon.patch(f"{LABELS}/{a['id']}", json={"name": "x"}, headers=team.h["dave"])
    ).status_code == 404
    unknown = await anon.patch(f"{LABELS}/999", json={"name": "x"}, headers=h)
    assert unknown.status_code == 404 and unknown.json() == {"detail": LABEL_NOT_FOUND}


async def test_delete_label_detaches_it_from_tasks(team, anon):
    label, task = await _label(anon, team), await _task(anon, team)
    await anon.post(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=team.h["alice"])
    assert (
        await anon.delete(f"{LABELS}/{label['id']}", headers=team.h["carol"])
    ).status_code == 403
    assert (await anon.delete(f"{LABELS}/{label['id']}", headers=team.h["bob"])).status_code == 204
    got = await anon.get(f"{TASKS}/{task['id']}", headers=team.h["alice"])
    assert got.status_code == 200 and got.json()["labels"] == []


# ------------------------------------------------------------ gắn / gỡ
async def test_attach_and_detach_label(team, anon):
    label, task = await _label(anon, team, "bug", color="#FF0000"), await _task(anon, team)
    url = f"{TASKS}/{task['id']}/labels/{label['id']}"
    r = await anon.post(url, headers=team.h["bob"])
    assert r.status_code == 200
    assert [lb["name"] for lb in r.json()["labels"]] == ["bug"]
    assert r.json()["labels"][0]["color"] == "#FF0000"
    # idempotent: gắn lần nữa không tạo bản sao
    again = await anon.post(url, headers=team.h["bob"])
    assert again.status_code == 200 and len(again.json()["labels"]) == 1
    # task trả về kèm labels ở mọi endpoint đọc
    assert (
        len((await anon.get(f"{TASKS}/{task['id']}", headers=team.h["carol"])).json()["labels"])
        == 1
    )
    listed = (await anon.get(f"{PRJ}/{team.project['id']}/tasks", headers=team.h["carol"])).json()
    assert [lb["name"] for lb in listed["items"][0]["labels"]] == ["bug"]
    # gỡ (cũng idempotent)
    assert (await anon.delete(url, headers=team.h["bob"])).json()["labels"] == []
    assert (await anon.delete(url, headers=team.h["bob"])).status_code == 200


async def test_task_can_have_many_labels(team, anon):
    task = await _task(anon, team)
    for name in ("a", "b", "c"):
        label = await _label(anon, team, name)
        r = await anon.post(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=team.h["alice"])
    assert sorted(lb["name"] for lb in r.json()["labels"]) == ["a", "b", "c"]


async def test_attach_rbac_and_errors(team, anon):
    label, task = await _label(anon, team), await _task(anon, team)
    url = f"{TASKS}/{task['id']}/labels/{label['id']}"
    assert (await anon.post(url, headers=team.h["carol"])).status_code == 403  # VIEWER
    assert (await anon.post(url, headers=team.h["dave"])).status_code == 404  # người ngoài
    unknown = await anon.post(f"{TASKS}/{task['id']}/labels/999", headers=team.h["alice"])
    assert unknown.status_code == 404 and unknown.json() == {"detail": LABEL_NOT_FOUND}
    assert (
        await anon.post(f"{TASKS}/999/labels/{label['id']}", headers=team.h["alice"])
    ).status_code == 404


async def test_cannot_attach_label_from_another_project(team, anon):
    other = await _other_project(anon, team)
    foreign = (
        await anon.post(f"{PRJ}/{other['id']}/labels", json={"name": "x"}, headers=team.h["alice"])
    ).json()
    task = await _task(anon, team)
    r = await anon.post(f"{TASKS}/{task['id']}/labels/{foreign['id']}", headers=team.h["alice"])
    assert r.status_code == 400 and r.json() == {"detail": LABEL_NOT_IN_PROJECT}


async def test_archived_project_blocks_label_changes(team, anon):
    label, task = await _label(anon, team), await _task(anon, team)
    await anon.post(f"{PRJ}/{team.project['id']}/archive", headers=team.h["alice"])
    h = team.h["alice"]
    create = await anon.post(_labels_url(team), json={"name": "new"}, headers=h)
    assert create.status_code == 409 and create.json() == {"detail": PROJECT_ARCHIVED}
    assert (
        await anon.patch(f"{LABELS}/{label['id']}", json={"name": "z"}, headers=h)
    ).status_code == 409
    attach = await anon.post(f"{TASKS}/{task['id']}/labels/{label['id']}", headers=h)
    assert attach.status_code == 409
    assert (await anon.get(_labels_url(team), headers=team.h["carol"])).status_code == 200
