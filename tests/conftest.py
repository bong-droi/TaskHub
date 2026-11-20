from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import enable_sqlite_fk, get_db
from app.main import app
from app.models import Project, User, Workspace, WorkspaceMember
from app.models.enums import UserRole, WorkspaceRole

EMAIL = "t@t.dev"
PASSWORD = "secret123"


@pytest.fixture(autouse=True)
def fast_bcrypt(monkeypatch):
    """Giảm cost bcrypt trong test cho nhanh (production vẫn dùng 12)."""
    monkeypatch.setattr("app.core.security.BCRYPT_ROUNDS", 4)


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
        user = User(
            email=EMAIL, full_name="T", hashed_password=hash_password(PASSWORD), role=UserRole.ADMIN
        )
        ws = Workspace(name="WS", owner=user)
        ws.members.append(WorkspaceMember(user=user, role=WorkspaceRole.OWNER))
        ws.projects.append(Project(name="P"))
        db.add_all([user, ws])
        await db.commit()
        return {"user_id": user.id, "project_id": ws.projects[0].id}


@pytest.fixture
async def anon(session_factory, seeded):
    """Client CHƯA đăng nhập."""

    async def override_get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
async def client(anon):
    """Client đã đăng nhập bằng user seed (dùng cho test /tasks, /users)."""
    r = await anon.post("/api/v1/auth/login", data={"username": EMAIL, "password": PASSWORD})
    anon.headers["Authorization"] = f"Bearer {r.json()['access_token']}"
    return anon


# ---------------------------------------------------------------- RBAC helpers
WS = "/api/v1/workspaces"


@pytest.fixture
def make_user(session_factory):
    """Tạo user (mật khẩu = PASSWORD) và trả về id."""

    async def _make(email, role=UserRole.MEMBER, full_name="User"):
        async with session_factory() as db:
            u = User(
                email=email,
                full_name=full_name,
                hashed_password=hash_password(PASSWORD),
                role=role,
            )
            db.add(u)
            await db.commit()
            return u.id

    return _make


@pytest.fixture
def auth(anon):
    """Đăng nhập và trả về header Authorization của một email."""

    async def _headers(email):
        r = await anon.post("/api/v1/auth/login", data={"username": email, "password": PASSWORD})
        assert r.status_code == 200
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    return _headers


@pytest.fixture
async def team(anon, make_user, auth):
    """alice = OWNER, bob = EDITOR, carol = VIEWER, dave = người ngoài workspace.

    Workspace "Team" có 1 project "P". Dùng `anon` + header riêng cho từng người."""
    names = ("alice", "bob", "carol", "dave")
    ids = {n: await make_user(f"{n}@t.dev", full_name=n.title()) for n in names}
    h = {n: await auth(f"{n}@t.dev") for n in names}
    ws = (await anon.post(WS, json={"name": "Team"}, headers=h["alice"])).json()
    for name, role in (("bob", "EDITOR"), ("carol", "VIEWER")):
        r = await anon.post(
            f"{WS}/{ws['id']}/members",
            json={"email": f"{name}@t.dev", "role": role},
            headers=h["alice"],
        )
        assert r.status_code == 201
    project = (
        await anon.post(f"{WS}/{ws['id']}/projects", json={"name": "P"}, headers=h["alice"])
    ).json()
    return SimpleNamespace(ids=ids, h=h, ws=ws, project=project)
