from __future__ import annotations
import asyncio, os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from models.enums import UserRole, UserStatus
from models.user import User
from security.auth import hash_password

ADMIN_EMAIL = "admin@karpathys.dev"
ADMIN_PASSWORD = "Karpathys2025!"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/karpathys")

async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        if result.scalar_one_or_none():
            print(f"Admin already exists: {ADMIN_EMAIL}")
        else:
            session.add(User(
                id=uuid.uuid4(),
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                full_name="Internal Admin",
                role=UserRole.admin,
                status=UserStatus.active,
            ))
            await session.commit()
            print(f"Created admin: {ADMIN_EMAIL}")
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed())
