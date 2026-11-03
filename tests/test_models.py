"""Kiểm tra relationships & cascade ở tầng ORM."""
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
import pytest

from app.models import Label, Project, Task, User
from app.models.task import task_labels


async def test_task_labels_many_to_many(session_factory, seeded):
    async with session_factory() as db:
        task = Task(title="t", project_id=seeded["project_id"])
        label = Label(name="bug", project_id=seeded["project_id"])
        task.labels.append(label)
        db.add(task)
        await db.commit()
        rows = (await db.execute(select(task_labels))).all()
        assert len(rows) == 1


async def test_cascade_delete_project_removes_tasks(session_factory, seeded):
    async with session_factory() as db:
        db.add(Task(title="t", project_id=seeded["project_id"]))
        await db.commit()
        project = await db.get(Project, seeded["project_id"])
        await db.delete(project)
        await db.commit()
        assert (await db.scalars(select(Task))).all() == []


async def test_unique_email(session_factory, seeded):
    async with session_factory() as db:
        db.add(User(email="t@t.dev", full_name="dup", hashed_password="x"))
        with pytest.raises(IntegrityError):
            await db.commit()
