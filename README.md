# TaskHub – Ngày 1: Core Setup & Architecture

Skeleton FastAPI với kiến trúc 3 lớp **Router → Service → Repository**.

## Chạy
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```
Swagger: http://127.0.0.1:8000/docs  |  ReDoc: http://127.0.0.1:8000/redoc

## Test
```bash
pytest -q
```

## Cấu trúc
```
app/
├── main.py                 # FastAPI instance + lifespan
├── core/config.py          # cấu hình
├── api/deps.py             # Dependency Injection
├── api/v1/router.py        # gom router
├── api/v1/endpoints/       # health, tasks
├── schemas/task.py         # Pydantic v2: Create / Update / Read
├── services/               # business logic
└── repositories/           # data access (in-memory, Ngày 2 -> SQLAlchemy)
tests/test_tasks.py         # TestClient + dependency_overrides
```

## Endpoints
`GET /api/v1/health`, `GET|POST /api/v1/tasks`, `GET|PATCH|DELETE /api/v1/tasks/{id}`
