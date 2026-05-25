"""Seed initial admin user for internal alpha.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python scripts/seed_admin.py

Idempotent — skips if admin@karpathys.dev already exists.
"""
from __future__ import annotations

import asyncio
import os
import sys
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

# Resolve backend root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models so SQLAlchemy mapper can resolve all relationships
import models.ai_decision  # noqa: F401, E402
import models.approval  # noqa: F401, E402
import models.audit_log  # noqa: F401, E402
import models.call  # noqa: F401, E402
import models.call_event  # noqa: F401, E402
import models.call_participant  # noqa: F401, E402
import models.call_session  # noqa: F401, E402
import models.lead  # noqa: F401, E402
import models.notification  # noqa: F401, E402
import models.property  # noqa: F401, E402
import models.realtime_session  # noqa: F401, E402
import models.transcript  # noqa: F401, E402
import models.transcript_chunk  # noqa: F401, E402
import models.transcript_event  # noqa: F401, E402
import models.transcript_segment  # noqa: F401, E402
import models.workflow  # noqa: F401, E402
import models.workflow_event  # noqa: F401, E402
from models.enums import UserRole, UserStatus  # noqa: E402
from models.user import User  # noqa: E402
from security.auth import hash_password  # noqa: E402

ADMIN_EMAIL = "admin@karpathys.dev"
ADMIN_PASSWORD = "admin1234"
ADMIN_NAME = "Internal Admin"

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql+asyncpg://angelowashington@localhost:5432/karpathys_dev",
)


async def seed() -> None:
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == ADMIN_EMAIL))
        existing = result.scalar_one_or_none()

        if existing:
            print(f"Admin already exists: {ADMIN_EMAIL} (id={existing.id})")
        else:
            admin = User(
                id=uuid.uuid4(),
                email=ADMIN_EMAIL,
                hashed_password=hash_password(ADMIN_PASSWORD),
                full_name=ADMIN_NAME,
                role=UserRole.admin,
                status=UserStatus.active,
            )
            session.add(admin)
            await session.commit()
            print(f"Created admin: {ADMIN_EMAIL} (id={admin.id})")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
