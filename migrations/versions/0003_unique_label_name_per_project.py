"""unique label name per project (case-insensitive)

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-18 02:20:21.793726
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_labels_project_id_lower_name"


def upgrade() -> None:
    # Unique index trên (project_id, lower(name)): "Bug" và "bug" trong cùng project là trùng.
    # Nếu DB đã có label trùng tên (khác hoa thường) trong cùng project, lệnh này sẽ lỗi:
    # hãy đổi tên các label đó trước khi nâng cấp.
    op.create_index(INDEX_NAME, "labels", ["project_id", sa.text("lower(name)")], unique=True)


def downgrade() -> None:
    op.drop_index(INDEX_NAME, table_name="labels")
