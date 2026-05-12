"""
Test configuration.

Schema lifecycle:
- pytest_sessionstart: nuke + recreate via subprocess psql (no asyncio involvement)
- pytest_sessionfinish: nuke via subprocess psql

Per-test isolation: SAVEPOINT rollback on `db` fixture.
Each test gets a fresh engine in its own event loop — no stale loop references.
"""

import asyncio
import subprocess

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import models.ai_decision  # noqa: F401
import models.approval  # noqa: F401
import models.audit_log  # noqa: F401
import models.call  # noqa: F401
import models.lead  # noqa: F401
import models.notification  # noqa: F401
import models.property  # noqa: F401
import models.realtime_session  # noqa: F401
import models.transcript  # noqa: F401
import models.transcript_chunk  # noqa: F401
import models.transcript_event  # noqa: F401
import models.transcript_segment  # noqa: F401
import models.user  # noqa: F401
import models.workflow  # noqa: F401
import models.workflow_event  # noqa: F401

# Import all models to populate Base.metadata before create_all
from db.session import Base

TEST_DB_URL = "postgresql+asyncpg://angelowashington@localhost:5432/karpathys_test"
PSQL = "/opt/homebrew/Cellar/postgresql@16/16.11_1/bin/psql"
PSQL_ARGS = [PSQL, "-h", "localhost", "-U", "angelowashington", "-d", "karpathys_test"]


def _nuke() -> None:
    subprocess.run(
        PSQL_ARGS + ["-c", "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"],
        check=True, capture_output=True,
    )


def _create_tables_sync() -> None:
    async def _run() -> None:
        engine = create_async_engine(TEST_DB_URL, echo=False)
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
        finally:
            await engine.dispose()

    asyncio.run(_run())


def pytest_sessionstart(session) -> None:  # noqa: ARG001
    _nuke()
    _create_tables_sync()


def pytest_sessionfinish(session, exitstatus) -> None:  # noqa: ARG001
    _nuke()


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    """
    Per-test session in its own event loop / engine.
    SAVEPOINT rollback — no data leaks between tests.
    """
    engine = create_async_engine(TEST_DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.begin()
            await conn.begin_nested()  # SAVEPOINT

            session = AsyncSession(bind=conn, expire_on_commit=False)
            yield session

            await session.close()
            await conn.rollback()
    finally:
        await engine.dispose()


@pytest.fixture(scope="session")
def client():
    from api.main import app
    with TestClient(app) as c:
        yield c
