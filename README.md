# TaskHub – FastAPI Training Project

Sample app xây dần theo từng ngày. Kiến trúc: **Router → Service → Repository → DB**.

| Ngày | Nội dung | Tag |
|---|---|---|
| 1 | Core Setup, Routing, Pydantic v2, DI (in-memory) | `day-1` |
| 2 | SQLAlchemy 2.x async, Repository Pattern, Alembic | `day-2` |
| 3 | Authentication & Security: bcrypt, JWT access/refresh, profile | `day-3` |

## Chạy nhanh (SQLite)
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # tuỳ chọn, mặc định dùng SQLite
alembic upgrade head            # tạo bảng
python -m scripts.seed          # dữ liệu mẫu (project_id=1)
uvicorn app.main:app --reload
```
Swagger: http://127.0.0.1:8000/docs

Đăng nhập (seed): `admin@taskhub.dev` / `Admin@12345`. Trong Swagger bấm **Authorize**, nhập email vào ô `username`.

Thử tạo task (cần token): `POST /api/v1/tasks` với `{"title": "Hello", "project_id": 1}`

## Auth (Ngày 3)
| Endpoint | Mô tả |
|---|---|
| `POST /auth/register` | Đăng ký (role luôn là MEMBER) |
| `POST /auth/login` | Form `username`(=email) + `password` -> access + refresh token |
| `POST /auth/refresh` | Đổi refresh token lấy cặp mới (rotation, mỗi token dùng 1 lần) |
| `POST /auth/logout` | Thu hồi refresh token |
| `GET/PATCH /users/me` | Xem / sửa profile |
| `POST /users/me/password` | Đổi mật khẩu, thu hồi mọi refresh token |

- Mật khẩu băm bằng **bcrypt**; JWT bằng **PyJWT** (HS256), access 15 phút, refresh 7 ngày.
- Refresh token lưu `jti` trong bảng `refresh_tokens` để thu hồi; dùng lại token đã xoay sẽ thu hồi cả chuỗi.
- **Đặt `SECRET_KEY` riêng** trong `.env` khi chạy thật.
- Toàn bộ `/tasks` yêu cầu đăng nhập; `tasks.created_by` lấy từ user hiện tại.
- Lỗi auth là exception nghiệp vụ (`UnauthorizedException`, `ConflictException`...) + message trong `core/constants.py`.
- Schema chứa mật khẩu **không** kế thừa `BaseSchema` (không được strip mật khẩu).
- Chưa làm (các ngày sau): RBAC theo workspace/project, middleware, Redis cache, Docker.

## PostgreSQL / MySQL
Đổi `DATABASE_URL` (xem `.env.example`) và cài driver `asyncpg` hoặc `aiomysql`, rồi chạy lại `alembic upgrade head`.

## Test
```bash
pytest -q        # dùng SQLite in-memory, không đụng taskhub.db
```

## Alembic cheat-sheet
```bash
alembic revision --autogenerate -m "mô tả"   # sinh migration từ thay đổi model
alembic upgrade head                          # áp dụng
alembic downgrade -1                          # lùi 1 bước
alembic check                                 # model và DB có lệch nhau không
```

## Cấu trúc (Ngày 2)
```
app/
├── main.py                  # app + lifespan (dispose engine)
├── core/config.py           # DATABASE_URL, JWT settings
├── core/security.py         # bcrypt + JWT
├── db/base.py, session.py   # Base, naming convention, engine, get_db (yield)
├── models/                  # 8 bảng: users, workspaces, workspace_members, projects,
│                            #         tasks, labels, task_labels, comments
├── repositories/base.py     # BaseRepository[T]: get/list/count/create/update/delete
├── services/                # business logic (async)
├── schemas/                 # Pydantic v2 + Page[T]
└── api/                     # deps.py (DI), v1/endpoints
migrations/                  # Alembic async env + 0001_initial_schema, 0002_add_refresh_tokens
scripts/seed.py
tests/                       # API tests + model/cascade tests
```

## Ghi chú thiết kế
- `expire_on_commit=False` để object vẫn đọc được sau commit khi dùng async.
- SQLite cần bật `PRAGMA foreign_keys=ON` (đã làm trong `db/session.py`).
- `tasks.created_by` đang nullable; Ngày 3 (Auth) sẽ gán từ `current_user`.
- Repository tự `commit`; có thể nâng cấp lên Unit of Work nếu cần transaction đa repo.

## Lint & format (ruff)
```bash
ruff format .          # định dạng (indent 4 space, quote kép, 100 cột)
ruff check .           # lint (import, bugbear, cấm print...)
ruff check --fix .     # tự sửa phần sửa được
```
Chạy cả hai lệnh trước mỗi commit. Cấu hình ở `pyproject.toml`, `.editorconfig` giữ indent thống nhất.

## Quy ước (rút ra từ review)
- PATCH: `exclude_unset` không loại `null` gửi tường minh -> field NOT NULL phải chặn null trong `*Update`.
- Service raise `NotFoundException` (`core/exceptions.py`), message nằm trong `core/constants.py`.
- Schema đầu vào kế thừa `BaseSchema` (tự cắt khoảng trắng đầu/cuối).
