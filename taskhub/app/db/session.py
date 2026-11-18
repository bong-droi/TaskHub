from collections.abc import AsyncIterator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import DATABASE_URL


def enable_sqlite_fk(engine: AsyncEngine) -> None:
    """SQLite mặc định KHÔNG kiểm tra foreign key, cần bật thủ công."""
    if engine.dialect.name != "sqlite":
        return

    @event.listens_for(engine.sync_engine, "connect")
    def _set_pragma(dbapi_conn, _record):  # noqa: ANN001
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


engine = create_async_engine(DATABASE_URL)
enable_sqlite_fk(engine)

# expire_on_commit=False: object vẫn đọc được sau commit (tránh lazy-load ngoài ý muốn trong async)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    """Dependency có yield: mỗi request một session, tự đóng khi xong."""
    async with SessionLocal() as session:
        yield session
