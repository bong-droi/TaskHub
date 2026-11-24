# TaskHub – FastAPI Training Project

Sample app xây dần theo từng ngày. Kiến trúc: **Router → Service → Repository → DB**.

| Ngày | Nội dung | Tag |
|---|---|---|
| 1 | Core Setup, Routing, Pydantic v2, DI (in-memory) | `day-1` |
| 2 | SQLAlchemy 2.x async, Repository Pattern, Alembic | `day-2` |
| 3 | Authentication & Security: bcrypt, JWT access/refresh, profile | `day-3` |
| 4 | Authorization & RBAC, Workspace, Project | `day-4` |
| 5 | Task nâng cao (lọc, phân trang), Label, Comment, Middleware | `day-5` |

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
├── core/permissions.py      # ma trận quyền theo role
├── core/middleware.py       # request id, process time, access log
├── services/                # business logic (async), access.py = kiểm tra quyền
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

## Phân quyền RBAC (Ngày 4)
Role trong workspace: **OWNER**, **EDITOR**, **VIEWER**. User có role hệ thống **ADMIN** (seed) được coi như OWNER của mọi workspace.

| Hành động | OWNER | EDITOR | VIEWER |
|---|:-:|:-:|:-:|
| Xem workspace, project, task | x | x | x |
| Tạo/sửa project, archive project | x | x | |
| Tạo/sửa task | x | x | |
| Xoá task | mọi task | chỉ task mình tạo | |
| Sửa/xoá workspace, xoá project, mời/xoá thành viên | x | | |

- **Không phải thành viên -> 404** (không lộ resource có tồn tại hay không); **là thành viên nhưng thiếu quyền -> 403**.
- Ma trận quyền nằm một chỗ: `app/core/permissions.py`; kiểm tra quyền: `app/services/access.py`.
- Assignee của task phải là thành viên của workspace. Project đã archive là read-only (409 khi sửa/tạo task).
- `GET /tasks` chỉ trả task thuộc workspace mình là thành viên.

| Endpoint | Quyền |
|---|---|
| `POST/GET /workspaces`, `GET /workspaces/{id}` | đăng nhập / thành viên |
| `PATCH/DELETE /workspaces/{id}` | OWNER |
| `POST/GET /workspaces/{id}/members`, `DELETE .../members/{user_id}` | OWNER mời/xoá, thành viên xem |
| `POST/GET /workspaces/{id}/projects` | OWNER/EDITOR tạo, thành viên xem |
| `GET/PATCH /projects/{id}`, `POST /projects/{id}/archive` | thành viên xem, OWNER/EDITOR sửa |
| `DELETE /projects/{id}` | OWNER |

## Task nâng cao, Label, Comment, Middleware (Ngày 5)

### Phân trang và lọc
Mọi endpoint danh sách dùng `?page=1&limit=20` (`page` từ 1, `limit` tối đa 100) và trả về:
`{"items": [...], "total": 42, "page": 1, "limit": 20, "pages": 3}`.

`GET /projects/{id}/tasks` lọc được theo `status`, `priority`, `assignee_id`, `label_id` (kết hợp bằng AND):
```
GET /api/v1/projects/1/tasks?status=TODO&priority=HIGH&assignee_id=2&page=1&limit=10
```

| Endpoint | Quyền |
|---|---|
| `GET/POST /projects/{id}/tasks` | thành viên xem, OWNER/EDITOR tạo (project_id lấy từ URL) |
| `PATCH /tasks/{id}` (đổi status, priority, due_date, assignee) | OWNER/EDITOR |
| `POST/GET /projects/{id}/labels`, `PATCH/DELETE /labels/{id}` | thành viên xem, OWNER/EDITOR ghi |
| `POST/DELETE /tasks/{id}/labels/{label_id}` | OWNER/EDITOR (idempotent) |
| `POST/GET /tasks/{id}/comments` | OWNER/EDITOR thêm, thành viên xem |
| `DELETE /comments/{id}` | tác giả, hoặc OWNER |

- Tên label duy nhất trong project (không phân biệt hoa thường); màu dạng `#RRGGBB`.
- Chỉ gắn được label cùng project với task (400 nếu khác project).
- Task trả về kèm danh sách `labels`.
- Project đã archive: không tạo/sửa task, label, comment (409); vẫn xem và xoá được.

### Middleware và xử lý lỗi
- Mọi response có `X-Request-ID` (nhận từ client nếu hợp lệ, không thì tự sinh) và `X-Process-Time`; mỗi request được ghi một dòng access log kèm request id.
- Lỗi không lường trước trả `500` chung chung `{"detail": ..., "request_id": ...}`, **không lộ stack trace**; chi tiết chỉ nằm trong log, tra theo `request_id`.
- Vi phạm ràng buộc DB lọt qua service (hai request cùng lúc) trả `409` thay vì `500`.

### Giới hạn đầu vào (tránh lỗi 500 do số quá lớn)
Mọi số nguyên đầu vào đều có cận trên, vì số vượt giới hạn của DB sẽ làm truy vấn lỗi (500) thay vì từ chối bằng 422:

| Đầu vào | Giới hạn | Định nghĩa |
|---|---|---|
| id trên URL (`/projects/{project_id}`, ...) | `1 .. 2147483647` | `IdPath` trong `app/api/params.py` |
| id trong body, filter `assignee_id`, `label_id` | `1 .. 2147483647` | `DbId` trong `app/schemas/types.py` |
| `page` | `1 .. 100000` (offset tối đa 10 triệu) | `Pagination` trong `app/api/deps.py` |

Khi thêm endpoint mới, **dùng `IdPath` cho id trên URL và `DbId` cho id trong schema**. `tests/test_input_bounds.py` quét toàn bộ endpoint theo OpenAPI nên endpoint nào quên giới hạn sẽ bị bắt.

### Quy ước code (rút ra từ review)
- **Một chỗ duy nhất** lấy resource + kiểm quyền + kiểm archive: `app/services/resource_access.py` (`ResourceAccess`). Service không tự viết lại `get -> 404 -> kiểm quyền`; luật project archive chỉ nằm ở `ensure_active`.
- `create_task(user, project_id, payload)` nhận `project_id` riêng, không dựng lại schema trong service.
- Schema PATCH dùng `not_nullable(...)` (`schemas/base.py`) cho field NOT NULL; mọi message validation nằm trong `core/constants.py` (có test chặn viết cứng).
- **Tên label không phân biệt hoa thường** (`Bug` = `bug`), được bảo đảm bởi unique index `(project_id, lower(name))`. Lưu ý: `lower()` của SQLite chỉ xử lý chữ ASCII (`Đỏ` khác `đỏ`); PostgreSQL xử lý đủ Unicode.

> **Nâng cấp từ bản cũ của migration `0003`:** migration này đã được sửa (đổi ràng buộc thường sang unique index không phân biệt hoa thường). Nếu DB của bạn đã chạy `0003` cũ, `alembic upgrade head` sẽ **không làm gì** và `alembic check` báo lệch. Cách sửa: với DB dev SQLite, xoá `taskhub.db` rồi chạy lại `alembic upgrade head` và `python -m scripts.seed`. Với DB cần giữ dữ liệu: chạy `alembic downgrade 0002` **trước khi** cập nhật code, rồi `alembic upgrade head` sau khi cập nhật.

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
