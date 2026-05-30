from __future__ import annotations
import os, sys, uuid
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

DATABASE_URL = os.environ.get("DATABASE_URL", "").replace("postgresql+asyncpg://", "postgresql://").replace("postgres://", "postgresql://")

ADMIN_EMAIL = "admin@karpathys.dev"
ADMIN_PASSWORD = "Karpathys2025!"

def seed() -> None:
    engine = create_engine(DATABASE_URL, echo=False)
    with Session(engine) as session:
        result = session.execute(text("SELECT id FROM users WHERE email = :email"), {"email": ADMIN_EMAIL})
        if result.fetchone():
            print(f"Admin already exists: {ADMIN_EMAIL}")
            return
        import bcrypt
        pw = bcrypt.hashpw(ADMIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
        session.execute(text("""
            INSERT INTO users (id, email, hashed_password, full_name, role, status, is_active, created_at, updated_at)
            VALUES (:id, :email, :pw, 'Internal Admin', 'admin', 'active', true, now(), now())
        """), {"id": str(uuid.uuid4()), "email": ADMIN_EMAIL, "pw": pw})
        session.commit()
        print(f"Created admin: {ADMIN_EMAIL}")

if __name__ == "__main__":
    seed()
