"""Cấu hình cơ bản. Ngày 6 sẽ nâng cấp lên pydantic-settings (fail-fast validation)."""

import os

from dotenv import load_dotenv

load_dotenv()  # đọc .env nếu có

APP_NAME = "TaskHub"
APP_VERSION = "0.3.0"
API_PREFIX = "/api/v1"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./taskhub.db")

# --- Auth ---
# Giá trị mặc định CHỈ để dev. Production phải đặt SECRET_KEY qua biến môi trường.
SECRET_KEY = os.getenv("SECRET_KEY", "change-me-dev-only-secret-key-32chars-min")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "15"))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
