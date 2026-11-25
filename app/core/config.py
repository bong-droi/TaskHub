"""Cấu hình ứng dụng bằng pydantic-settings: đọc từ biến môi trường và file .env.

- **Fail-fast:** cấu hình sai thì app KHÔNG khởi động được, báo rõ field nào sai, thay vì chạy
  tiếp rồi lỗi lúc đang xử lý request.
- **Nhiều môi trường:** đặt biến môi trường `APP_ENV` (development | test | production).
  Thứ tự ưu tiên (cao -> thấp): biến môi trường thật > `.env.<APP_ENV>` > `.env` > giá trị mặc định.
  `APP_ENV` phải là biến môi trường thật (không đọc từ file) vì nó quyết định file nào được nạp.
"""

import os
from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Hằng số của ứng dụng (không đổi theo môi trường)
APP_NAME = "TaskHub"
APP_VERSION = "0.6.0"
API_PREFIX = "/api/v1"
ALGORITHM = "HS256"

DEV_SECRET_KEY = "change-me-dev-only-secret-key-32chars-min"
MIN_SECRET_KEY_LENGTH = 32  # HS256 cần khoá tối thiểu 256 bit
MIN_PRODUCTION_BCRYPT_ROUNDS = 10
# Engine là async nên bắt buộc dùng driver async (vd "sqlite://" thường sẽ lỗi lúc chạy)
ASYNC_DATABASE_PREFIXES = ("sqlite+aiosqlite://", "postgresql+asyncpg://", "mysql+aiomysql://")
REDIS_URL_PREFIXES = ("redis://", "rediss://", "unix://")

_app_env = os.getenv("APP_ENV", "development")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", f".env.{_app_env}"),  # file sau đè file trước
        env_file_encoding="utf-8",  # Windows mặc định cp1252 sẽ lỗi với ký tự tiếng Việt
        case_sensitive=True,
        extra="ignore",
    )

    APP_ENV: Literal["development", "test", "production"] = "development"

    # --- Database ---
    DATABASE_URL: str = "sqlite+aiosqlite:///./taskhub.db"

    # --- Auth ---
    SECRET_KEY: SecretStr = SecretStr(DEV_SECRET_KEY)  # SecretStr: không lộ khi print/log
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=15, gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, gt=0)
    BCRYPT_ROUNDS: int = Field(default=12, ge=4, le=16)

    # --- Cache (Redis). Để trống = tắt cache ---
    REDIS_URL: str = ""
    CACHE_TTL_SECONDS: int = Field(default=60, gt=0)

    # --- Email ---
    EMAIL_BACKEND: Literal["console", "smtp"] = "console"  # console: chỉ ghi log (dev/test)
    EMAIL_FROM: str = "TaskHub <no-reply@taskhub.dev>"
    SMTP_HOST: str = ""
    SMTP_PORT: int = Field(default=587, gt=0, lt=65536)
    SMTP_USER: str = ""
    SMTP_PASSWORD: SecretStr = SecretStr("")
    SMTP_STARTTLS: bool = True

    # --- Logging ---
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # ------------------------------------------------------------------ validation
    @field_validator("DATABASE_URL")
    @classmethod
    def database_must_use_async_driver(cls, v: str) -> str:
        if not v.startswith(ASYNC_DATABASE_PREFIXES):
            raise ValueError(
                "DATABASE_URL phải dùng driver async, bắt đầu bằng một trong "
                f"{ASYNC_DATABASE_PREFIXES}"
            )
        return v

    @field_validator("REDIS_URL")
    @classmethod
    def redis_url_must_be_valid(cls, v: str) -> str:
        if v and not v.startswith(REDIS_URL_PREFIXES):
            raise ValueError(f"REDIS_URL phải bắt đầu bằng một trong {REDIS_URL_PREFIXES}")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_must_be_long_enough(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"SECRET_KEY phải dài ít nhất {MIN_SECRET_KEY_LENGTH} ký tự")
        return v

    @model_validator(mode="after")
    def validate_environment_rules(self) -> Self:
        if self.EMAIL_BACKEND == "smtp" and not self.SMTP_HOST:
            raise ValueError("EMAIL_BACKEND=smtp yêu cầu phải đặt SMTP_HOST")
        if self.APP_ENV == "production":
            if self.SECRET_KEY.get_secret_value() == DEV_SECRET_KEY:
                raise ValueError(
                    "Production không được dùng SECRET_KEY mặc định của môi trường dev"
                )
            if self.BCRYPT_ROUNDS < MIN_PRODUCTION_BCRYPT_ROUNDS:
                raise ValueError(f"Production cần BCRYPT_ROUNDS >= {MIN_PRODUCTION_BCRYPT_ROUNDS}")
        return self

    # ------------------------------------------------------------------ tiện ích
    @property
    def cache_enabled(self) -> bool:
        return bool(self.REDIS_URL)

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


settings = Settings()  # nạp và kiểm tra ngay khi import: sai cấu hình thì dừng ở đây
