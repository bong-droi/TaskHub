"""Kiểu tham số dùng chung cho endpoint. Mọi id trên URL phải dùng `IdPath` để id sai (0, âm,
vượt giới hạn DB) bị chặn ngay ở router với 422, không lọt xuống DB thành lỗi 500."""

from typing import Annotated

from fastapi import Path

from app.core.constants import MAX_DB_ID

IdPath = Annotated[int, Path(ge=1, le=MAX_DB_ID)]
