import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object
config = context.config

# Logging setup
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base and all models so autogenerate can detect them
# Models are imported here once Phase 3 backend core is implemented
import models.ai_decision  # noqa: E402, F401
import models.approval  # noqa: E402, F401
import models.audit_log  # noqa: E402, F401
import models.call  # noqa: E402, F401
import models.lead  # noqa: E402, F401
import models.notification  # noqa: E402, F401
import models.property  # noqa: E402, F401
import models.realtime_session  # noqa: E402, F401
import models.transcript  # noqa: E402, F401
import models.transcript_segment  # noqa: E402, F401

# Import all models for Alembic autogenerate detection
import models.user  # noqa: E402, F401
import models.workflow  # noqa: E402, F401
import models.workflow_event  # noqa: E402, F401
from db.session import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
