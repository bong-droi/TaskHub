import logging

from app.models import Project, Task, User
from app.models.enums import TaskPriority
from app.services.notifier import build_assignment_email

PRJ = "/api/v1/projects"
TASKS = "/api/v1/tasks"


def _url(team):
    return f"{PRJ}/{team.project['id']}/tasks"


async def _create(anon, team, who="alice", **extra):
    return await anon.post(
        _url(team), json={"title": "Sửa lỗi đăng nhập", **extra}, headers=team.h[who]
    )


# ------------------------------------------------------------------ khi nào có email
async def test_assigning_someone_else_sends_one_email(team, anon, outbox):
    r = await _create(
        anon, team, priority="HIGH", due_date="2999-12-31", assignee_id=team.ids["bob"]
    )
    assert r.status_code == 201
    assert len(outbox.sent) == 1
    mail = outbox.sent[0]
    assert mail.to == "bob@t.dev"
    assert "Sửa lỗi đăng nhập" in mail.subject
    for expected in ("Bob", "Alice", '"P"', "HIGH", "2999-12-31", f"#{r.json()['id']}"):
        assert expected in mail.body, expected


async def test_no_email_without_assignee_or_when_assigning_yourself(team, anon, outbox):
    await _create(anon, team)
    await _create(anon, team, assignee_id=team.ids["alice"])  # tự giao cho mình
    assert outbox.sent == []


async def test_patch_assignment_rules(team, anon, outbox):
    task = (await _create(anon, team)).json()
    url, h = f"{TASKS}/{task['id']}", team.h["alice"]
    bob, carol = team.ids["bob"], team.ids["carol"]

    await anon.patch(url, json={"assignee_id": bob}, headers=h)  # chưa giao -> giao
    assert [m.to for m in outbox.sent] == ["bob@t.dev"]
    await anon.patch(url, json={"assignee_id": bob}, headers=h)  # giao lại đúng người cũ
    await anon.patch(url, json={"title": "Đổi tên"}, headers=h)  # đổi field khác
    assert len(outbox.sent) == 1
    await anon.patch(url, json={"assignee_id": carol}, headers=h)  # đổi người -> chỉ báo người mới
    assert [m.to for m in outbox.sent] == ["bob@t.dev", "carol@t.dev"]
    await anon.patch(url, json={"assignee_id": None}, headers=h)  # bỏ gán -> không báo
    assert len(outbox.sent) == 2


async def test_legacy_task_route_also_notifies(team, anon, outbox):
    r = await anon.post(
        TASKS,
        json={"title": "T", "project_id": team.project["id"], "assignee_id": team.ids["carol"]},
        headers=team.h["alice"],
    )
    assert r.status_code == 201 and [m.to for m in outbox.sent] == ["carol@t.dev"]


# ------------------------------------------------------------------ thất bại thì không gửi
async def test_no_email_when_the_request_fails(team, anon, outbox):
    body = {"assignee_id": team.ids["bob"]}
    assert (await _create(anon, team, who="carol", **body)).status_code == 403  # VIEWER
    assert (await _create(anon, team, who="dave", **body)).status_code == 404  # người ngoài
    outsider = {"assignee_id": team.ids["dave"]}  # assignee không thuộc workspace
    assert (await _create(anon, team, **outsider)).status_code == 400
    assert (await _create(anon, team, assignee_id=999)).status_code == 404
    await anon.post(f"{PRJ}/{team.project['id']}/archive", headers=team.h["alice"])
    assert (await _create(anon, team, **body)).status_code == 409  # project đã archive
    assert outbox.sent == []


# ------------------------------------------------------------------ gửi nền, lỗi không ảnh hưởng
async def test_email_failure_never_breaks_the_request(team, anon, outbox, caplog):
    outbox.fail = True
    caplog.set_level(logging.ERROR, logger="taskhub.notifier")
    r = await _create(anon, team, assignee_id=team.ids["bob"])
    assert r.status_code == 201 and r.json()["assignee_id"] == team.ids["bob"]  # task vẫn được tạo
    task_id = r.json()["id"]
    assert any(
        "Gửi email thất bại" in m
        and f"user_id={team.ids['bob']}" in m
        and f"task_id={task_id}" in m
        for m in caplog.messages
    )
    assert all("bob@t.dev" not in m for m in caplog.messages)  # không lộ email (PII) trong log lỗi
    got = await anon.get(f"{TASKS}/{task_id}", headers=team.h["alice"])
    assert got.status_code == 200


# ------------------------------------------------------------------ nội dung email
def _fixtures(due_date=None):
    task = Task(id=7, title="Viết báo cáo", priority=TaskPriority.URGENT, due_date=due_date)
    project = Project(id=1, name="Website")
    assignee = User(id=2, email="an@t.dev", full_name="An")
    assigner = User(id=1, email="binh@t.dev", full_name="Bình")
    return task, project, assignee, assigner


def test_email_content_without_due_date():
    mail = build_assignment_email(*_fixtures())
    assert mail.to == "an@t.dev" and mail.subject == "[TaskHub] Bạn được giao task: Viết báo cáo"
    assert "chưa đặt" in mail.body and "URGENT" in mail.body and "Bình" in mail.body
    assert 'project "Website"' in mail.body and "#7" in mail.body


def test_email_content_with_due_date():
    from datetime import date

    mail = build_assignment_email(*_fixtures(due_date=date(2030, 1, 15)))
    assert "2030-01-15" in mail.body and "chưa đặt" not in mail.body
