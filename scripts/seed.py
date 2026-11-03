"""Tạo dữ liệu mẫu: 1 user, 1 workspace, 1 project.  Chạy: python -m scripts.seed"""
import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models import Project, User, Workspace, WorkspaceMember
from app.models.enums import UserRole, WorkspaceRole


async def main() -> None:
    async with SessionLocal() as db:
        if await db.scalar(select(User).where(User.email == "admin@taskhub.dev")):
            print("Đã có dữ liệu mẫu, bỏ qua.")
            return
        # hashed_password là placeholder; Ngày 3 sẽ băm bằng passlib/bcrypt
        user = User(email="admin@taskhub.dev", full_name="Admin",
                    hashed_password="placeholder", role=UserRole.ADMIN)
        ws = Workspace(name="Demo Workspace", owner=user)
        ws.members.append(WorkspaceMember(user=user, role=WorkspaceRole.OWNER))
        ws.projects.append(Project(name="Demo Project", description="Project mẫu"))
        db.add_all([user, ws])
        await db.commit()
        print(f"Seed xong: user_id={user.id}, workspace_id={ws.id}, project_id=1")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
