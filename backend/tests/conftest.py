"""
Test configuration.

Schema lifecycle:
- pytest_sessionstart: nuke + recreate via subprocess psql (no asyncio involvement)
- pytest_sessionfinish: nuke via subprocess psql

Per-test isolation: SAVEPOINT rollback on `db` fixture.
Each test gets a fresh engine in its own event loop — no stale loop references.

Singleton reset: `_reset_singletons` autouse fixture clears module-level caches
between every test so state cannot leak across test boundaries.
"""

import asyncio
import os
from uuid import UUID

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

import models.ai_decision  # noqa: F401
import models.ai_execution  # noqa: F401
import models.approval  # noqa: F401
import models.approval_delegation  # noqa: F401
import models.audit_log  # noqa: F401
import models.call  # noqa: F401
import models.call_event  # noqa: F401
import models.call_participant  # noqa: F401
import models.call_session  # noqa: F401
import models.context_snapshot  # noqa: F401
import models.domain_event  # noqa: F401
import models.governance_event  # noqa: F401
import models.governance_policy  # noqa: F401
import models.lead  # noqa: F401
import models.notification  # noqa: F401
import models.property  # noqa: F401
import models.realtime_session  # noqa: F401
import models.research_event  # noqa: F401
import models.research_evidence  # noqa: F401
import models.research_job  # noqa: F401
import models.research_memory  # noqa: F401
import models.research_plan  # noqa: F401
import models.research_task  # noqa: F401
import models.research_task_dependency  # noqa: F401
import models.sophia_event  # noqa: F401
import models.sophia_session  # noqa: F401
import models.sophia_turn  # noqa: F401
import models.transcript  # noqa: F401
import models.transcript_checkpoint  # noqa: F401
import models.transcript_chunk  # noqa: F401
import models.transcript_event  # noqa: F401
import models.transcript_segment  # noqa: F401
import models.transcript_stream  # noqa: F401
import models.user  # noqa: F401
import models.workflow  # noqa: F401
import models.workflow_checkpoint  # noqa: F401
import models.workflow_event  # noqa: F401
import models.workflow_lease  # noqa: F401
import models.workflow_snapshot  # noqa: F401

# Import all models to populate Base.metadata before create_all
from db.base import Base
from testing.database import validate_disposable_database

TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "")


def _nuke() -> None:
    validate_disposable_database(TEST_DB_URL)
    async def reset():
        engine = create_async_engine(TEST_DB_URL)
        try:
            async with engine.begin() as connection:
                await connection.execute(text("DROP SCHEMA public CASCADE"))
                await connection.execute(text("CREATE SCHEMA public"))
        finally:
            await engine.dispose()
    asyncio.run(reset())


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


@pytest.fixture(autouse=True)
def _reset_singletons() -> None:
    """
    Clear module-level mutable singletons before each test.

    Prevents context cache hits from one test bleeding into the next.
    Add other stateful singletons here as they are introduced.
    """
    from context.assembler import _cache  # noqa: PLC0415
    _cache.clear()
    yield
    _cache.clear()


@pytest.fixture(scope="session")
def client():
    from api.main import app
    from models.enums import UserRole, UserStatus
    from security.auth import get_current_active_user

    class _FakeUser:
        id = UUID("00000000-0000-0000-0000-000000000001")
        email = "test@internal"
        role = UserRole.admin
        status = UserStatus.active
        full_name = "Test Admin"

    app.dependency_overrides[get_current_active_user] = lambda: _FakeUser()
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.pop(get_current_active_user, None)
