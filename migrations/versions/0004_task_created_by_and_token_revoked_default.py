"""task created_by not null + index, refresh_tokens revoked server_default

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-27 10:30:00.000000
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_constraint(op.f("fk_tasks_created_by_users"), type_="foreignkey")
        batch_op.alter_column("created_by", existing_type=sa.Integer(), nullable=False)
        batch_op.create_foreign_key(
            op.f("fk_tasks_created_by_users"),
            "users",
            ["created_by"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch_op.create_index(batch_op.f("ix_tasks_created_by"), ["created_by"], unique=False)

    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.alter_column(
            "revoked",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        )


def downgrade() -> None:
    with op.batch_alter_table("refresh_tokens", schema=None) as batch_op:
        batch_op.alter_column(
            "revoked",
            existing_type=sa.Boolean(),
            nullable=False,
            server_default=None,
        )

    with op.batch_alter_table("tasks", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tasks_created_by"))
        batch_op.drop_constraint(op.f("fk_tasks_created_by_users"), type_="foreignkey")
        batch_op.alter_column("created_by", existing_type=sa.Integer(), nullable=True)
        batch_op.create_foreign_key(
            op.f("fk_tasks_created_by_users"),
            "users",
            ["created_by"],
            ["id"],
            ondelete="SET NULL",
        )
