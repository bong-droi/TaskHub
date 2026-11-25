from app.core.constants import PROJECT_ARCHIVED, PROJECT_NOT_FOUND

PRJ = "/api/v1/projects"
TASKS = "/api/v1/tasks"


def _url(team, query=""):
    return f"{PRJ}/{team.project['id']}/tasks{query}"


async def _mk(anon, team, title, who="alice", **extra):
    r = await anon.post(_url(team), json={"title": title, **extra}, headers=team.h[who])
    assert r.status_code == 201, r.text
    return r.json()


async def _titles(anon, team, query="", who="alice"):
    r = await anon.get(_url(team, query), headers=team.h[who])
    assert r.status_code == 200, r.text
    return [t["title"] for t in r.json()["items"]], r.json()


async def _seed_tasks(anon, team):
    """t1 HIGH/bob, t2 LOW/carol (IN_PROGRESS), t3 HIGH/không ai, t4 MEDIUM/bob (DONE)."""
    bob, carol = team.ids["bob"], team.ids["carol"]
    await _mk(anon, team, "t1", priority="HIGH", assignee_id=bob)
    t2 = await _mk(anon, team, "t2", priority="LOW", assignee_id=carol)
    await _mk(anon, team, "t3", priority="HIGH")
    t4 = await _mk(anon, team, "t4", priority="MEDIUM", assignee_id=bob)
    h = team.h["alice"]
    await anon.patch(f"{TASKS}/{t2['id']}", json={"status": "IN_PROGRESS"}, headers=h)
    await anon.patch(f"{TASKS}/{t4['id']}", json={"status": "DONE"}, headers=h)
    return t2, t4


async def test_no_filter_returns_all_with_pagination_meta(team, anon):
    await _seed_tasks(anon, team)
    titles, body = await _titles(anon, team)
    assert titles == ["t1", "t2", "t3", "t4"]
    assert body["total"] == 4 and body["page"] == 1 and body["pages"] == 1


async def test_filter_by_status(team, anon):
    await _seed_tasks(anon, team)
    assert (await _titles(anon, team, "?status=DONE"))[0] == ["t4"]
    assert (await _titles(anon, team, "?status=IN_PROGRESS"))[0] == ["t2"]
    assert (await _titles(anon, team, "?status=TODO"))[0] == ["t1", "t3"]
    assert (await _titles(anon, team, "?status=IN_REVIEW"))[0] == []


async def test_filter_by_priority_and_assignee(team, anon):
    await _seed_tasks(anon, team)
    assert (await _titles(anon, team, "?priority=HIGH"))[0] == ["t1", "t3"]
    assert (await _titles(anon, team, f"?assignee_id={team.ids['bob']}"))[0] == ["t1", "t4"]
    assert (await _titles(anon, team, f"?assignee_id={team.ids['alice']}"))[0] == []


async def test_filters_combine_with_and_and_total_reflects_filter(team, anon):
    await _seed_tasks(anon, team)
    query = f"?priority=HIGH&assignee_id={team.ids['bob']}"
    titles, body = await _titles(anon, team, query)
    assert titles == ["t1"] and body["total"] == 1
    assert (await _titles(anon, team, "?priority=HIGH&status=DONE"))[0] == []


async def test_filter_by_label(team, anon):
    t2, _ = await _seed_tasks(anon, team)
    label = (
        await anon.post(
            f"{PRJ}/{team.project['id']}/labels", json={"name": "bug"}, headers=team.h["alice"]
        )
    ).json()
    await anon.post(f"{TASKS}/{t2['id']}/labels/{label['id']}", headers=team.h["alice"])
    assert (await _titles(anon, team, f"?label_id={label['id']}"))[0] == ["t2"]


async def test_filter_plus_pagination(team, anon):
    for i in range(5):
        await _mk(anon, team, f"h{i}", priority="HIGH")
    await _mk(anon, team, "low", priority="LOW")
    titles, body = await _titles(anon, team, "?priority=HIGH&page=2&limit=2")
    assert titles == ["h2", "h3"] and body["total"] == 5 and body["pages"] == 3
    titles, body = await _titles(anon, team, "?priority=HIGH&page=3&limit=2")
    assert titles == ["h4"]
    assert (await _titles(anon, team, "?priority=HIGH&page=4&limit=2"))[0] == []


async def test_invalid_query_params_are_rejected(team, anon):
    for bad in ("status=BOGUS", "priority=URGENTISH", "assignee_id=0", "label_id=abc",
                "page=0", "limit=101"):  # fmt: skip
        r = await anon.get(_url(team, f"?{bad}"), headers=team.h["alice"])
        assert r.status_code == 422, bad


async def test_list_rbac(team, anon):
    await _mk(anon, team, "t1")
    for who in ("alice", "bob", "carol"):  # mọi thành viên đều xem được
        assert (await _titles(anon, team, who=who))[0] == ["t1"]
    assert (await anon.get(_url(team), headers=team.h["dave"])).status_code == 404
    unknown = await anon.get(f"{PRJ}/999/tasks", headers=team.h["alice"])
    assert unknown.status_code == 404 and unknown.json() == {"detail": PROJECT_NOT_FOUND}


async def test_nested_create_rules(team, anon):
    body = {"title": "  Việc mới  "}
    ok = await anon.post(_url(team), json=body, headers=team.h["bob"])
    assert ok.status_code == 201
    task = ok.json()
    assert task["title"] == "Việc mới" and task["project_id"] == team.project["id"]
    assert task["created_by"] == team.ids["bob"] and task["labels"] == []
    assert (await anon.post(_url(team), json=body, headers=team.h["carol"])).status_code == 403
    assert (await anon.post(_url(team), json=body, headers=team.h["dave"])).status_code == 404
    assert (
        await anon.post(f"{PRJ}/999/tasks", json=body, headers=team.h["alice"])
    ).status_code == 404


async def test_nested_create_ignores_project_id_in_body(team, anon):
    """project_id chỉ lấy từ URL: client không thể tạo task vào project khác bằng body."""
    other = (
        await anon.post(
            f"/api/v1/workspaces/{team.ws['id']}/projects",
            json={"name": "Other"},
            headers=team.h["alice"],
        )
    ).json()
    r = await anon.post(
        _url(team), json={"title": "x", "project_id": other["id"]}, headers=team.h["alice"]
    )
    assert r.status_code == 201 and r.json()["project_id"] == team.project["id"]


async def test_nested_create_validation_and_assignee_rule(team, anon):
    h = team.h["alice"]
    assert (await anon.post(_url(team), json={"title": "   "}, headers=h)).status_code == 422
    past = {"title": "x", "due_date": "2000-01-01"}
    assert (await anon.post(_url(team), json=past, headers=h)).status_code == 422
    outsider = {"title": "x", "assignee_id": team.ids["dave"]}  # dave không thuộc workspace
    assert (await anon.post(_url(team), json=outsider, headers=h)).status_code == 400


async def test_status_workflow_and_archived_project(team, anon):
    task = await _mk(anon, team, "flow", who="bob")
    url = f"{TASKS}/{task['id']}"
    for status in ("IN_PROGRESS", "IN_REVIEW", "DONE", "TODO"):
        r = await anon.patch(url, json={"status": status}, headers=team.h["bob"])
        assert r.status_code == 200 and r.json()["status"] == status
    await anon.post(f"{PRJ}/{team.project['id']}/archive", headers=team.h["alice"])
    locked = await anon.post(_url(team), json={"title": "n"}, headers=team.h["alice"])
    assert locked.status_code == 409 and locked.json() == {"detail": PROJECT_ARCHIVED}
    assert (await _titles(anon, team))[0] == ["flow"]  # vẫn xem/lọc được khi đã archive
