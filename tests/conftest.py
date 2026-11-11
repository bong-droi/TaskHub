import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import enable_sqlite_fk, get_db
from app.main import app
from app.models import Project, User, Workspace
from app.models.enums import UserRole


@pytest.fixture
async def session_factory():
    """SQLite in-memory riêng cho mỗi test -> test độc lập, không đụng file .db."""
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    enable_sqlite_fk(engine)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield async_sessionmaker(engine, expire_on_commit=False)
    await engine.dispose()


@pytest.fixture
async def seeded(session_factory):
    async with session_factory() as db:
        user = User(email="t@t.dev", full_name="T", hashed_password="x", role=UserRole.ADMIN)
        ws = Workspace(name="WS", owner=user)
        ws.projects.append(Project(name="P"))
        db.add_all([user, ws])
        await db.commit()
        return {"user_id": user.id, "project_id": ws.projects[0].id}


@pytest.fixture
async def client(session_factory, seeded):
    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
