from __future__ import annotations
import asyncio, os, sys, uuid
import bcrypt

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://")

ADMIN_EMAIL = "admin@karpathys.dev"
ADMIN_PASSWORD = "Karpathys2025!"

async def seed() -> None:
    import asyncpg
    url = DATABASE_URL.replace("postgresql://", "")
    conn = await asyncpg.connect(f"postgresql://{url}" if not url.startswith("postgres") else DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://"))
    existing = await conn.fetchrow("SELECT id FROM users WHERE email = $1", ADMIN_EMAIL)
    if existing:
        print(f"Admin already exists: {ADMIN_EMAIL}")
    else:
        pw = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        await conn.execute("""
            INSERT INTO users (id, email, hashed_password, full_name, role, status, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, 'Internal Admin', 'admin', 'active', true, now(), now())
        """, str(uuid.uuid4()), ADMIN_EMAIL, pw)
        print(f"Created admin: {ADMIN_EMAIL}")
    await conn.close()

if __name__ == "__main__":
    asyncio.run(seed())
