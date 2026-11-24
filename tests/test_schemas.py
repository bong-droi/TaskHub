"""Quy ước của schema: PATCH không nhận null cho field NOT NULL, thông báo lỗi nằm trong
constants, id đầu vào có giới hạn."""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.constants import FIELD_CANNOT_BE_NULL, MAX_DB_ID, PASSWORD_TOO_LONG
from app.schemas.auth import RegisterRequest
from app.schemas.label import LabelUpdate
from app.schemas.project import ProjectUpdate
from app.schemas.task import TaskCreate, TaskCreateInProject, TaskUpdate
from app.schemas.workspace import WorkspaceUpdate

ROOT = Path(__file__).resolve().parent.parent  # chạy pytest ở thư mục nào cũng được

# (schema PATCH, field NOT NULL, field nullable thật sự)
PATCH_SCHEMAS = [
    (TaskUpdate, ["title", "status", "priority"], ["description", "due_date", "assignee_id"]),
    (ProjectUpdate, ["name"], ["description"]),
    (WorkspaceUpdate, ["name"], []),
    (LabelUpdate, ["name", "color"], []),
]
NOT_NULL_CASES = [(s, f) for s, fields, _ in PATCH_SCHEMAS for f in fields]
NULLABLE_CASES = [(s, f) for s, _, fields in PATCH_SCHEMAS for f in fields]


@pytest.mark.parametrize(("schema", "field"), NOT_NULL_CASES)
def test_not_nullable_fields_reject_explicit_null_with_the_shared_message(schema, field):
    with pytest.raises(ValidationError) as exc:
        schema.model_validate({field: None})
    (error,) = exc.value.errors()
    assert error["loc"] == (field,)  # lỗi gắn đúng field, client biết field nào sai
    assert error["msg"] == f"Value error, {FIELD_CANNOT_BE_NULL}"


@pytest.mark.parametrize(("schema", "field"), NULLABLE_CASES)
def test_really_nullable_fields_still_accept_null(schema, field):
    assert schema.model_validate({field: None}).model_dump(exclude_unset=True) == {field: None}


@pytest.mark.parametrize("schema", [s for s, _, _ in PATCH_SCHEMAS])
def test_omitted_fields_are_fine_and_stay_unset(schema):
    assert schema.model_validate({}).model_dump(exclude_unset=True) == {}


def test_every_schema_message_comes_from_constants():
    """Chặn tái phạm review #6: không được viết cứng chuỗi trong ValueError của schema."""
    pattern = re.compile(r"ValueError\(\s*f?[\"']")
    offenders = [
        f"{path.name}:{i}"
        for path in sorted((ROOT / "app" / "schemas").glob("*.py"))
        for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if pattern.search(line)
    ]
    assert offenders == [], f"viết cứng message trong schema, hãy đưa vào constants.py: {offenders}"


def test_password_too_long_message_is_formatted_from_the_constant():
    with pytest.raises(ValidationError) as exc:
        RegisterRequest(email="a@t.dev", password="ế" * 30, full_name="A")
    assert PASSWORD_TOO_LONG.format(max_bytes=72) in exc.value.errors()[0]["msg"]


def test_due_date_message_comes_from_constants():
    with pytest.raises(ValidationError) as exc:
        TaskCreateInProject(title="x", due_date="2000-01-01")
    assert "quá khứ" in exc.value.errors()[0]["msg"]


# ---------------------------------------------------------------- DbId
@pytest.mark.parametrize("bad", [0, -1, MAX_DB_ID + 1, 10**20])
def test_ids_in_schemas_are_bounded(bad):
    with pytest.raises(ValidationError):
        TaskCreate(title="x", project_id=bad)
    with pytest.raises(ValidationError):
        TaskCreateInProject(title="x", assignee_id=bad)
    with pytest.raises(ValidationError):
        TaskUpdate(assignee_id=bad)


def test_largest_valid_id_is_accepted_and_none_means_unassigned():
    assert TaskCreate(title="x", project_id=MAX_DB_ID).project_id == MAX_DB_ID
    assert TaskCreateInProject(title="x").assignee_id is None
    assert TaskUpdate(assignee_id=None).assignee_id is None


def test_task_create_is_an_in_project_body_plus_project_id():
    assert issubclass(TaskCreate, TaskCreateInProject)
    assert "project_id" not in TaskCreateInProject.model_fields
