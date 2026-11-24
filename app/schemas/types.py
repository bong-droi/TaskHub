"""Kiểu dùng chung cho schema.

Mọi id đầu vào đều phải qua `DbId`: dương và không vượt giới hạn DB.
"""

from typing import Annotated

from pydantic import Field

from app.core.constants import MAX_DB_ID

DbId = Annotated[int, Field(gt=0, le=MAX_DB_ID)]
