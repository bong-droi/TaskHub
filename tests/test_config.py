import subprocess
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import DEV_SECRET_KEY, Settings

GOOD_SECRET = "x" * 40
ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Biến môi trường của máy dev không được lọt vào test."""
    for name in Settings.model_fields:
        monkeypatch.delenv(name, raising=False)


def make(**overrides) -> Settings:
    return Settings(_env_file=None, **overrides)  # không đọc .env thật


def test_defaults_are_valid_for_development():
    s = make()
    assert s.APP_ENV == "development" and not s.is_production
    assert s.SECRET_KEY.get_secret_value() == DEV_SECRET_KEY
    assert s.cache_enabled is False and s.EMAIL_BACKEND == "console"


# ---------------------------------------------------------------- production
def test_production_rejects_default_secret_key():
    with pytest.raises(ValidationError, match="SECRET_KEY mặc định"):
        make(APP_ENV="production")


def test_production_accepts_real_secret():
    s = make(APP_ENV="production", SECRET_KEY=GOOD_SECRET)
    assert s.is_production


def test_production_requires_strong_bcrypt():
    with pytest.raises(ValidationError, match="BCRYPT_ROUNDS"):
        make(APP_ENV="production", SECRET_KEY=GOOD_SECRET, BCRYPT_ROUNDS=4)
    assert make(APP_ENV="development", BCRYPT_ROUNDS=4).BCRYPT_ROUNDS == 4  # dev/test được phép


# ---------------------------------------------------------------- field rules
@pytest.mark.parametrize(("length", "ok"), [(31, False), (32, True), (64, True)])
def test_secret_key_minimum_length(length, ok):
    if ok:
        make(SECRET_KEY="k" * length)
    else:
        with pytest.raises(ValidationError, match="SECRET_KEY"):
            make(SECRET_KEY="k" * length)


@pytest.mark.parametrize(
    ("url", "ok"),
    [
        ("sqlite+aiosqlite:///./a.db", True),
        ("postgresql+asyncpg://u:p@h:5432/db", True),
        ("mysql+aiomysql://u:p@h:3306/db", True),
        ("sqlite:///./a.db", False),  # driver đồng bộ: engine async sẽ lỗi lúc chạy
        ("postgresql://u:p@h/db", False),
        ("", False),
    ],
)
def test_database_url_must_use_async_driver(url, ok):
    if ok:
        assert make(DATABASE_URL=url).DATABASE_URL == url
    else:
        with pytest.raises(ValidationError, match="DATABASE_URL"):
            make(DATABASE_URL=url)


def test_redis_url_validation_and_cache_switch():
    assert make(REDIS_URL="").cache_enabled is False
    assert make(REDIS_URL="redis://localhost:6379/0").cache_enabled is True
    assert make(REDIS_URL="rediss://h:6380/1").cache_enabled is True
    with pytest.raises(ValidationError, match="REDIS_URL"):
        make(REDIS_URL="localhost:6379")


def test_smtp_backend_requires_host():
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        make(EMAIL_BACKEND="smtp")
    assert make(EMAIL_BACKEND="smtp", SMTP_HOST="smtp.example.com").SMTP_PORT == 587


@pytest.mark.parametrize(
    "bad",
    [
        {"ACCESS_TOKEN_EXPIRE_MINUTES": 0},
        {"REFRESH_TOKEN_EXPIRE_DAYS": -1},
        {"BCRYPT_ROUNDS": 3},
        {"BCRYPT_ROUNDS": 17},
        {"CACHE_TTL_SECONDS": 0},
        {"SMTP_PORT": 0},
        {"SMTP_PORT": 70000},
        {"LOG_LEVEL": "TRACE"},
        {"APP_ENV": "staging"},
    ],
)
def test_out_of_range_values_are_rejected(bad):
    with pytest.raises(ValidationError):
        make(**bad)


def test_error_names_the_offending_field():
    with pytest.raises(ValidationError) as exc:
        make(BCRYPT_ROUNDS=99, CACHE_TTL_SECONDS=0)
    text = str(exc.value)
    assert "BCRYPT_ROUNDS" in text and "CACHE_TTL_SECONDS" in text  # báo hết một lượt


# ---------------------------------------------------------------- nguồn cấu hình
def test_environment_variables_are_read_and_parsed(monkeypatch):
    monkeypatch.setenv("REDIS_URL", "redis://cache:6379/2")
    monkeypatch.setenv("CACHE_TTL_SECONDS", "30")
    monkeypatch.setenv("SMTP_STARTTLS", "false")
    s = make()
    assert s.REDIS_URL == "redis://cache:6379/2"
    assert s.CACHE_TTL_SECONDS == 30 and s.SMTP_STARTTLS is False


def test_env_files_layer_and_real_env_wins(tmp_path, monkeypatch):
    base = tmp_path / ".env"
    prod = tmp_path / ".env.production"
    base.write_text("REDIS_URL=redis://base:6379/0\nCACHE_TTL_SECONDS=10\nLOG_LEVEL=DEBUG\n")
    prod.write_text("CACHE_TTL_SECONDS=99\n", encoding="utf-8")
    s = Settings(_env_file=(base, prod))
    assert s.REDIS_URL == "redis://base:6379/0"  # chỉ có ở .env
    assert s.CACHE_TTL_SECONDS == 99  # .env.production (nạp sau) đè .env
    assert s.LOG_LEVEL == "DEBUG"
    monkeypatch.setenv("CACHE_TTL_SECONDS", "5")  # biến môi trường thật thắng cả hai file
    assert Settings(_env_file=(base, prod)).CACHE_TTL_SECONDS == 5


def test_env_file_with_vietnamese_comments_is_readable(tmp_path):
    env = tmp_path / ".env"
    env.write_text("# Cấu hình thử: ký tự tiếng Việt\nCACHE_TTL_SECONDS=12\n", encoding="utf-8")
    assert Settings(_env_file=env).CACHE_TTL_SECONDS == 12  # không lỗi cp1252 trên Windows


def test_secrets_never_appear_in_repr():
    s = make(SECRET_KEY="hunter2-" + "x" * 32, SMTP_PASSWORD="smtp-pass-123")
    text = repr(s) + str(s)
    assert "hunter2" not in text and "smtp-pass-123" not in text


# ---------------------------------------------------------------- fail-fast thật sự
def test_app_refuses_to_start_with_invalid_config(tmp_path, monkeypatch):
    """Import cấu hình trong tiến trình mới với APP_ENV=production và khoá mặc định -> phải chết.

    Chạy ở thư mục trống (không có .env của máy dev) và giữ nguyên môi trường còn lại để Python
    khởi động được trên mọi hệ điều hành."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    result = subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode != 0
    assert "SECRET_KEY" in result.stderr
