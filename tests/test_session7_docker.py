"""Kiểm tra hành vi production mode: tắt /docs, /redoc, /openapi.json nhưng /health vẫn chạy."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


async def test_docs_are_enabled_in_non_production(anon) -> None:
    assert (await anon.get("/docs")).status_code == 200
    assert (await anon.get("/redoc")).status_code == 200
    assert (await anon.get("/openapi.json")).status_code == 200


def test_docs_are_disabled_in_production(tmp_path, monkeypatch) -> None:
    """Chạy trong tiến trình riêng với APP_ENV=production: /docs, /redoc, /openapi.json -> 404."""
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SECRET_KEY", "prod-secret-key-at-least-32-characters-long")
    monkeypatch.setenv("DATABASE_URL", f"sqlite+aiosqlite:///{tmp_path / 'prod.db'}")
    monkeypatch.setenv("PYTHONPATH", str(ROOT))
    script = (
        "from fastapi.testclient import TestClient; "
        "from app.main import app; "
        "c = TestClient(app); "
        "assert c.get('/api/v1/health').status_code == 200; "
        "assert c.get('/docs').status_code == 404; "
        "assert c.get('/redoc').status_code == 404; "
        "assert c.get('/openapi.json').status_code == 404"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
