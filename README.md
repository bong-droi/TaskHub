# TaskHub – FastAPI Production-Ready Project

Ứng dụng quản lý công việc (**Task Management RESTful API**) xây dựng bằng **FastAPI**, **SQLAlchemy 2.x Async**, **Alembic**, **Pydantic v2**, **Redis 7**, **PostgreSQL 16** theo kiến trúc phân tầng **Router → Service → Repository → Database**.

| Session / Ngày | Nội dung | Nhánh / Tag |
|---|---|---|
| 1 | Core Setup, Routing, Pydantic v2, Dependency Injection | `day-1` |
| 2 | SQLAlchemy 2.x Async, Repository Pattern, Alembic Migrations | `day-2` |
| 3 | Authentication & Security: bcrypt, JWT Access/Refresh Rotation, Profile | `day-3` |
| 4 | Authorization & RBAC (`OWNER` / `EDITOR` / `VIEWER`), Workspace, Project | `day-4` |
| 5 | Task Filtering & Pagination, Label, Comment, Request Context Middleware | `day-5` |
| 6 | Cấu hình `pydantic-settings`, Redis Cache (`X-Cache`), Background Email | `day-6` |
| 7 | Docker Multi-Stage Build (Non-Root User) & Docker Compose Stack (Postgres 16 + Redis 7) | `day-7` |
| 8 | Code Review, Refactor (DRY), Performance Optimization, Ruff/Mypy 100%, OpenAPI Error Docs & E2E Testing | `day-8` |

---

## 1. Cài đặt & Chạy Local (Development với SQLite)

```bash
python -m venv .venv
# Linux / macOS:
source .venv/bin/activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1

pip install -r requirements-dev.txt  # production chỉ cần: pip install -r requirements.txt
cp .env.example .env                 # BẮT BUỘC đặt SECRET_KEY (>= 32 ký tự) trong .env hoặc env
alembic upgrade head                 # Chạy migration tạo bảng
python -m scripts.seed               # Tạo dữ liệu mẫu (admin@taskhub.dev / Admin@12345)
uvicorn app.main:app --reload
```

- **Swagger UI**: http://127.0.0.1:8000/docs
- **ReDoc**: http://127.0.0.1:8000/redoc
- **Tài khoản mẫu (seed)**: `admin@taskhub.dev` / `Admin@12345` (bấm **Authorize** trong Swagger, nhập email vào ô `username`).

---

## 2. Chạy bằng Docker Compose (Session 7 – Production Stack)

Toàn bộ hạ tầng gồm **FastAPI App (`taskhub_app`) + PostgreSQL 16 (`taskhub_db`) + Redis 7 (`taskhub_redis`)** được khởi chạy chỉ bằng một lệnh:

```bash
cp .env.example .env
# Bắt buộc đặt SECRET_KEY tối thiểu 32 ký tự (khác giá trị mẫu khi APP_ENV=production):
# python -c "import secrets; print(secrets.token_urlsafe(32))"

docker compose up --build -d
```

### Điểm nổi bật của Docker Stack:
- **Multi-Stage `Dockerfile`**:
  - **Stage 1 (`builder`)**: Dùng `python:3.12-slim` cài đặt toàn bộ thư viện runtime trong `requirements.txt` vào `/install` với `--no-cache-dir`.
  - **Stage 2 (`runtime`)**: Chỉ copy `/install` từ stage `builder` và mã nguồn cần thiết (`app/`, `migrations/`, `scripts/`, `alembic.ini`).
  - **Non-Root User**: Chạy dưới quyền `appuser` (UID `1001`, group `appgroup`) thay vì `root`.
  - **Auto-Migrate**: Khi container khởi động, tự động chạy `alembic upgrade head` trước khi bật `uvicorn app.main:app --host 0.0.0.0 --port 8000`.
- **`.dockerignore`**: Loại bỏ `.venv`, `.env*`, `*.db`, `.git`, `__pycache__`, `.pytest_cache`, `.mypy_cache`, `.ruff_cache` để giảm kích thước image và không làm lộ bí mật local.
- **`docker-compose.yml`**:
  - `db` (`postgres:16-alpine`): Lưu trữ bền vững qua volume `postgres_data` và có `healthcheck` (`pg_isready`).
  - `redis` (`redis:7-alpine`): Có `healthcheck` (`redis-cli ping`).
  - `app` (`taskhub_app`): Bắt buộc khai báo `${SECRET_KEY:?Set SECRET_KEY in .env}` và chỉ khởi động sau khi `db` và `redis` đạt trạng thái `service_healthy`.

---

## 3. Biến môi trường (`.env`)

Mọi cấu hình được kiểm tra **fail-fast** khi khởi động tại `app/core/config.py`:

| Biến | Mặc định (dev) | Mô tả |
|---|---|---|
| `APP_ENV` | `development` | `development` \| `test` \| `production` (**phải đặt bằng OS env thật, không đặt trong `.env`**) |
| `DATABASE_URL` | `sqlite+aiosqlite:///./taskhub.db` | URL kết nối DB async (`sqlite+aiosqlite://`, `postgresql+asyncpg://`, `mysql+aiomysql://`) |
| `SECRET_KEY` | *(bắt buộc)* | Khoá ký JWT HS256 (tối thiểu 32 ký tự, **không có default**, chặn khoá mẫu trên production) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `15` | Thời hạn Access Token (phút) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Thời hạn Refresh Token (ngày) |
| `BCRYPT_ROUNDS` | `12` | Độ mạnh bcrypt (`4..16`, production `>= 10`) |
| `REDIS_URL` | `""` *(tắt cache)* | Ví dụ `redis://localhost:6379/0` (hoặc `redis://redis:6379/0` trong Docker Compose) |
| `CACHE_TTL_SECONDS` | `60` | TTL của cache danh sách task (`1 .. VERSION_TTL_SECONDS`) |
| `EMAIL_BACKEND` | `console` | `console` (ghi log không chứa email PII) hoặc `smtp` (gửi thật qua `SMTP_HOST`; chặn `SMTP_USER` khi `SMTP_STARTTLS=false`) |
| `LOG_LEVEL` | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` |

---

## 4. Kiến trúc, Tối ưu & Chất lượng mã nguồn (Session 8)

- **DRY (Don't Repeat Yourself)**:
  - Tập trung toàn bộ hằng số giới hạn độ dài, phân trang và thông báo lỗi tại `app/core/constants.py` (`TITLE_MIN_LENGTH`, `TITLE_MAX_LENGTH`, `PASSWORD_MAX_LENGTH = 72`, `DEFAULT_LIMIT`, `MAX_LIMIT = 100`, `VERSION_TTL_SECONDS`, `MEMORY_CACHE_MAX_KEYS`, v.v.).
  - `BaseSchema` (`app/schemas/base.py`) bật sẵn `str_strip_whitespace=True` và cung cấp `not_nullable` / `reject_explicit_nulls` để chặn `null` gửi tường minh vào các trường `NOT NULL` khi gọi `PATCH`.
  - Chuẩn hoá phân trang qua factory `Page.create()` / `PaginatedResponse.create()` (`app/schemas/common.py`).
  - Gom toàn bộ kiểm tra tồn tại + phân quyền RBAC + trạng thái archive của project về `ResourceAccess` (`app/services/resource_access.py`).
- **Tối ưu Database / Cache / Async**:
  - **SQLAlchemy Loading**: Không dùng `lazy="selectin"` tràn lan trên `User`/`Workspace`/`Project`/`Comment`; kết hợp `passive_deletes=True` để DB tự xử lý `ON DELETE CASCADE` và dùng `selectinload` tường minh tại `get_by_id_with_details`.
  - **Unit-of-Work Transaction**: `BaseRepository` hỗ trợ `flush()` và gom nhiều thao tác ghi (như tạo `Workspace` + thêm `WorkspaceMember` role `OWNER`) vào 1 lần `commit` duy nhất.
  - **Non-blocking Async**: Đưa `bcrypt` hashing/verification sang threadpool (`run_in_threadpool` trong `app/core/security.py`) để không làm nghẽn Event Loop của FastAPI.
- **OpenAPI Error Documentation**:
  - Chuẩn hoá `ErrorResponse` / `InternalErrorResponse` (`app/schemas/error.py`) và `error_responses(...)` (`app/api/responses.py`) cho toàn bộ endpoints trên Swagger UI & ReDoc.

---

## 5. Alembic Migration, Kiểm thử & Linter / Type Check

### Alembic Migrations
```bash
alembic revision --autogenerate -m "mô tả"   # Sinh migration mới từ thay đổi model
alembic upgrade head                          # Nâng cấp DB lên phiên bản mới nhất
alembic downgrade -1                          # Lùi 1 bước migration
alembic check                                 # Kiểm tra model và DB có khớp nhau không
```

### Chạy bộ Test (Unit + Integration + Docker + OpenAPI + E2E)
```bash
pytest -q
```

### Kiểm tra Code Quality (Ruff & Mypy 100%)
```bash
ruff check app tests          # Lint 0 lỗi, 0 cảnh báo
ruff format --check app tests # Kiểm tra định dạng chuẩn
mypy app tests                # Kiểm tra kiểu tĩnh 0 lỗi
```
