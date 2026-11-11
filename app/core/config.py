"""Cấu hình cơ bản. Ngày 6 sẽ nâng cấp lên pydantic-settings."""

import os

APP_NAME = "TaskHub"
APP_VERSION = "0.2.0"
API_PREFIX = "/api/v1"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./taskhub.db")
