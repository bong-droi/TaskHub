"""Kiểm tra relationships & cascade ở tầng ORM."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models import Label, Project, RefreshToken, Task, User
from app.models.task import task_labels


async def test_task_labels_many_to_many(session_factory, seeded):
    async with session_factory() as db:
        task = Task(title="t", project_id=seeded["project_id"], created_by=seeded["user_id"])
        label = Label(name="bug", project_id=seeded["project_id"])
        task.labels.append(label)
        db.add(task)
        await db.commit()
        rows = (await db.execute(select(task_labels))).all()
        assert len(rows) == 1


async def test_cascade_delete_project_removes_tasks(session_factory, seeded):
    async with session_factory() as db:
        db.add(Task(title="t", project_id=seeded["project_id"], created_by=seeded["user_id"]))
        await db.commit()
        project = await db.get(Project, seeded["project_id"])
        await db.delete(project)
        await db.commit()
        assert (await db.scalars(select(Task))).all() == []


async def test_task_requires_created_by(session_factory, seeded):
    async with session_factory() as db:
        db.add(Task(title="t", project_id=seeded["project_id"], created_by=None))
        with pytest.raises(IntegrityError):
            await db.commit()


async def test_refresh_token_revoked_has_server_default(session_factory, seeded):
    col = RefreshToken.__table__.c.revoked
    assert col.server_default is not None
    async with session_factory() as db:
        rt = RefreshToken(
            jti="jti-default-test",
            user_id=seeded["user_id"],
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        db.add(rt)
        await db.commit()
        await db.refresh(rt)
        assert rt.revoked is False


async def test_unique_email(session_factory, seeded):
    async with session_factory() as db:
        db.add(User(email="t@t.dev", full_name="dup", hashed_password="x"))
        with pytest.raises(IntegrityError):
            await db.commit()
