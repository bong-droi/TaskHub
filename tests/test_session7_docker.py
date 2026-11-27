"""Kiểm tra cấu hình Docker Multi-Stage Build, .dockerignore và Docker Compose Stack (Session 7)."""

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
DOCKERFILE = ROOT / "Dockerfile"
DOCKERIGNORE = ROOT / ".dockerignore"
COMPOSE_FILE = ROOT / "docker-compose.yml"


def test_dockerfile_exists_and_uses_multistage_build() -> None:
    assert DOCKERFILE.is_file(), "Thiếu tệp Dockerfile ở thư mục gốc"
    content = DOCKERFILE.read_text(encoding="utf-8")

    # Stage 1 (builder) & Stage 2 (runtime) đều dùng python:3.12-slim
    from_lines = [
        line.strip() for line in content.splitlines() if line.strip().upper().startswith("FROM ")
    ]
    assert len(from_lines) >= 2, "Dockerfile phải có ít nhất 2 stage (multi-stage build)"
    assert "python:3.12-slim" in from_lines[0] and "AS builder" in from_lines[0]
    assert "python:3.12-slim" in from_lines[1]

    # Cài thư viện vào /install không lưu cache pip và copy sang runtime stage
    assert "--no-cache-dir" in content
    assert "--prefix=/install" in content
    assert "COPY --from=builder /install" in content

    # Chỉ copy mã nguồn cần thiết
    assert "app/" in content
    assert "alembic.ini" in content
    assert "migrations/" in content or "alembic/" in content


def test_dockerfile_enforces_non_root_user_and_auto_migration_cmd() -> None:
    content = DOCKERFILE.read_text(encoding="utf-8")

    # Bảo mật Non-Root User: group appgroup, user appuser (UID 1001)
    assert "appgroup" in content
    assert "appuser" in content
    assert "1001" in content
    user_lines = [
        line.strip() for line in content.splitlines() if line.strip().upper().startswith("USER ")
    ]
    assert user_lines and user_lines[-1] == "USER appuser"

    # Tự động chạy alembic upgrade head trước khi bật uvicorn
    assert "alembic upgrade head" in content
    assert "uvicorn app.main:app --host 0.0.0.0 --port 8000" in content
    assert content.index("alembic upgrade head") < content.index(
        "uvicorn app.main:app --host 0.0.0.0 --port 8000"
    )


def test_dockerignore_excludes_sensitive_and_heavy_paths() -> None:
    assert DOCKERIGNORE.is_file(), "Thiếu tệp .dockerignore"
    lines = {
        line.strip().rstrip("/")
        for line in DOCKERIGNORE.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    required = {
        ".venv",
        ".env",
        "*.db",
        ".git",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
    }
    missing = required - lines
    assert not missing, f".dockerignore thiếu các mục bắt buộc: {sorted(missing)}"


def test_docker_compose_stack_configuration() -> None:
    assert COMPOSE_FILE.is_file(), "Thiếu tệp docker-compose.yml"
    raw = COMPOSE_FILE.read_text(encoding="utf-8")
    compose: dict[str, Any] = yaml.safe_load(raw)

    services = compose.get("services", {})
    assert {"db", "redis", "app"}.issubset(services.keys())

    # 1. Database service (PostgreSQL 16 + persistent volume + healthcheck)
    db = services["db"]
    assert db["image"] == "postgres:16-alpine"
    assert any("postgres_data:" in v for v in db.get("volumes", []))
    db_hc_test = " ".join(db["healthcheck"]["test"])
    assert "pg_isready" in db_hc_test

    # 2. Redis service (Redis 7 + healthcheck)
    redis = services["redis"]
    assert redis["image"] == "redis:7-alpine"
    redis_hc_test = " ".join(redis["healthcheck"]["test"])
    assert "redis-cli" in redis_hc_test and "ping" in redis_hc_test

    # 3. App service (taskhub_app + SECRET_KEY bắt buộc + depends_on service_healthy)
    app = services["app"]
    assert app.get("container_name") == "taskhub_app"
    assert ".env" in app.get("env_file", [])

    env = app.get("environment", {})
    secret_cfg = env.get("SECRET_KEY", "") if isinstance(env, dict) else " ".join(env)
    assert "${SECRET_KEY:?Set SECRET_KEY in .env}" in secret_cfg

    depends_on = app.get("depends_on", {})
    assert depends_on["db"]["condition"] == "service_healthy"
    assert depends_on["redis"]["condition"] == "service_healthy"

    # Top-level volume postgres_data
    assert "postgres_data" in compose.get("volumes", {})
