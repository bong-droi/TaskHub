"""Tạo dữ liệu mẫu: 1 admin, 1 workspace, 1 project.  Chạy: python -m scripts.seed"""

import asyncio
import logging

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models import Project, User, Workspace, WorkspaceMember
from app.models.enums import UserRole, WorkspaceRole

logger = logging.getLogger("seed")

ADMIN_EMAIL = "admin@taskhub.dev"
ADMIN_PASSWORD = "Admin@12345"  # chỉ dùng cho dev


async def main() -> None:
    async with SessionLocal() as db:
        user = await db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if user is not None:
            if user.hashed_password == "placeholder":  # dữ liệu seed từ Ngày 2
                user.hashed_password = hash_password(ADMIN_PASSWORD)
                await db.commit()
                logger.info(f"Đã cập nhật mật khẩu admin: {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
            else:
                logger.info("Đã có dữ liệu mẫu, bỏ qua.")
        else:
            user = User(
                email=ADMIN_EMAIL,
                full_name="Admin",
                hashed_password=hash_password(ADMIN_PASSWORD),
                role=UserRole.ADMIN,
            )
            ws = Workspace(name="Demo Workspace", owner=user)
            ws.members.append(WorkspaceMember(user=user, role=WorkspaceRole.OWNER))
            ws.projects.append(Project(name="Demo Project", description="Project mẫu"))
            db.add_all([user, ws])
            await db.commit()
            logger.info(f"Seed xong: {ADMIN_EMAIL} / {ADMIN_PASSWORD}, project_id=1")
    await engine.dispose()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    asyncio.run(main())
