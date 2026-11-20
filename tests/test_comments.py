from sqlalchemy import func, select

from app.core.constants import (
    COMMENT_NOT_FOUND,
    INSUFFICIENT_PERMISSION,
    PROJECT_ARCHIVED,
    TASK_NOT_FOUND,
)
from app.models import Comment

PRJ = "/api/v1/projects"
TASKS = "/api/v1/tasks"
COMMENTS = "/api/v1/comments"


async def _task(anon, team):
    r = await anon.post(
        f"{PRJ}/{team.project['id']}/tasks", json={"title": "T"}, headers=team.h["alice"]
    )
    return r.json()


async def _comment(anon, team, task, content="Xin chào", who="alice"):
    r = await anon.post(
        f"{TASKS}/{task['id']}/comments", json={"content": content}, headers=team.h[who]
    )
    assert r.status_code == 201, r.text
    return r.json()


async def test_add_comment_rules(team, anon):
    task = await _task(anon, team)
    r = await anon.post(
        f"{TASKS}/{task['id']}/comments", json={"content": "  Đã xong  "}, headers=team.h["bob"]
    )
    assert r.status_code == 201
    body = r.json()
    assert body["content"] == "Đã xong" and body["author_id"] == team.ids["bob"]
    assert body["task_id"] == task["id"] and body["created_at"]
    payload = {"content": "x"}
    url = f"{TASKS}/{task['id']}/comments"
    viewer = await anon.post(url, json=payload, headers=team.h["carol"])
    assert viewer.status_code == 403 and viewer.json() == {"detail": INSUFFICIENT_PERMISSION}
    outsider = await anon.post(url, json=payload, headers=team.h["dave"])
    assert outsider.status_code == 404 and outsider.json() == {"detail": TASK_NOT_FOUND}
    assert (
        await anon.post(f"{TASKS}/999/comments", json=payload, headers=team.h["alice"])
    ).status_code == 404


async def test_comment_validation(team, anon):
    url = f"{TASKS}/{(await _task(anon, team))['id']}/comments"
    h = team.h["alice"]
    for bad in ({"content": ""}, {"content": "   "}, {"content": "x" * 2001}, {}):
        assert (await anon.post(url, json=bad, headers=h)).status_code == 422
    assert (await anon.post(url, json={"content": "x" * 2000}, headers=h)).status_code == 201


async def test_list_is_oldest_first_paginated_and_visible_to_members(team, anon):
    task = await _task(anon, team)
    for i in range(5):
        await _comment(anon, team, task, f"c{i}")
    url = f"{TASKS}/{task['id']}/comments"
    page = (
        await anon.get(f"{url}?page=2&limit=2", headers=team.h["carol"])
    ).json()  # VIEWER đọc được
    assert [c["content"] for c in page["items"]] == ["c2", "c3"]
    assert page["total"] == 5 and page["pages"] == 3
    assert (await anon.get(url, headers=team.h["dave"])).status_code == 404
    assert (await anon.get(f"{TASKS}/999/comments", headers=team.h["alice"])).status_code == 404


async def test_delete_ownership_rules(team, anon):
    task = await _task(anon, team)
    bobs = await _comment(anon, team, task, "của bob", "bob")
    alices = await _comment(anon, team, task, "của alice", "alice")
    # EDITOR không xoá được comment của người khác
    other = await anon.delete(f"{COMMENTS}/{alices['id']}", headers=team.h["bob"])
    assert other.status_code == 403 and other.json() == {"detail": INSUFFICIENT_PERMISSION}
    assert (
        await anon.delete(f"{COMMENTS}/{alices['id']}", headers=team.h["carol"])
    ).status_code == 403
    assert (
        await anon.delete(f"{COMMENTS}/{alices['id']}", headers=team.h["dave"])
    ).status_code == 404
    # tác giả xoá comment của mình
    assert (await anon.delete(f"{COMMENTS}/{bobs['id']}", headers=team.h["bob"])).status_code == 204
    # OWNER xoá được comment của bất kỳ ai
    again = await _comment(anon, team, task, "bob lần 2", "bob")
    assert (
        await anon.delete(f"{COMMENTS}/{again['id']}", headers=team.h["alice"])
    ).status_code == 204
    remaining = (await anon.get(f"{TASKS}/{task['id']}/comments", headers=team.h["alice"])).json()
    assert [c["content"] for c in remaining["items"]] == ["của alice"]
    missing = await anon.delete(f"{COMMENTS}/999", headers=team.h["alice"])
    assert missing.status_code == 404 and missing.json() == {"detail": COMMENT_NOT_FOUND}


async def test_archived_project_blocks_new_comments_but_allows_delete(team, anon):
    task = await _task(anon, team)
    comment = await _comment(anon, team, task)
    await anon.post(f"{PRJ}/{team.project['id']}/archive", headers=team.h["alice"])
    r = await anon.post(
        f"{TASKS}/{task['id']}/comments", json={"content": "mới"}, headers=team.h["alice"]
    )
    assert r.status_code == 409 and r.json() == {"detail": PROJECT_ARCHIVED}
    assert (
        await anon.delete(f"{COMMENTS}/{comment['id']}", headers=team.h["alice"])
    ).status_code == 204


async def test_removed_member_loses_access_to_comments(team, anon):
    task = await _task(anon, team)
    comment = await _comment(anon, team, task, "của bob", "bob")
    await anon.delete(
        f"/api/v1/workspaces/{team.ws['id']}/members/{team.ids['bob']}", headers=team.h["alice"]
    )
    assert (
        await anon.delete(f"{COMMENTS}/{comment['id']}", headers=team.h["bob"])
    ).status_code == 404
    assert (
        await anon.get(f"{TASKS}/{task['id']}/comments", headers=team.h["bob"])
    ).status_code == 404


async def test_deleting_task_deletes_its_comments(team, anon, session_factory):
    task = await _task(anon, team)
    await _comment(anon, team, task)
    await _comment(anon, team, task, "hai")
    assert (await anon.delete(f"{TASKS}/{task['id']}", headers=team.h["alice"])).status_code == 204
    async with session_factory() as db:
        assert await db.scalar(select(func.count()).select_from(Comment)) == 0
