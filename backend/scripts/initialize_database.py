import argparse
import asyncio
import json
import os
from pathlib import Path

from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from config.settings import settings
from scripts.verify_schema import verify
from testing.database import validate_disposable_database

SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "db/schema_baselines/platform_v1.json"


def initialize(connection):
    script = ScriptDirectory.from_config(Config("alembic.ini"))
    heads = script.get_heads()
    if len(heads) != 1:
        raise RuntimeError("Schema initialization requires exactly one migration head")
    connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('platform_schema_initialization', 0))"))
    existing = set(inspect(connection).get_table_names()) - {"alembic_version"}
    context = MigrationContext.configure(connection)
    if not existing:
        if inspect(connection).get_enums():
            raise RuntimeError("Existing enum types require a reviewed reconciliation plan")
        snapshot = json.loads(SNAPSHOT_PATH.read_text())
        for statement in snapshot["upgrade"]:
            connection.exec_driver_sql(statement)
        verify(connection)
        context.stamp(script, heads[0])
        print("Initialized frozen platform schema and recorded existing migration head")
    else:
        verify(connection)
        if context.get_current_heads() != tuple(heads):
            raise RuntimeError("Existing database requires a reviewed migration; it will not be automatically stamped")
        print("Existing schema and migration head verified without changing application data")


def reset_test_snapshot(connection):
    snapshot = json.loads(SNAPSHOT_PATH.read_text())
    if set(inspect(connection).get_table_names()) - {"alembic_version"} != set(snapshot["tables"]):
        raise RuntimeError("Test reset refused: schema differs from the frozen baseline")
    for statement in snapshot["downgrade"]:
        connection.exec_driver_sql(statement)
    MigrationContext.configure(connection).stamp(ScriptDirectory.from_config(Config("alembic.ini")), "base")


async def main(roundtrip=False):
    url = os.environ.get("DATABASE_URL", "")
    if not url.startswith("postgresql+asyncpg://"):
        raise RuntimeError("An explicit PostgreSQL async DATABASE_URL is required")
    if settings.is_production and settings.is_secret_key_insecure:
        raise RuntimeError("Production signing configuration must be secured before initialization")
    if roundtrip:
        if url != os.environ.get("TEST_DATABASE_URL"):
            raise RuntimeError("Round-trip target must match TEST_DATABASE_URL")
        validate_disposable_database(url)
    engine = create_async_engine(url, poolclass=NullPool, connect_args={"timeout": 10, "command_timeout": 30})
    try:
        async with asyncio.timeout(120):
            async with engine.begin() as connection:
                await connection.run_sync(initialize)
            if roundtrip:
                async with engine.begin() as connection:
                    await connection.run_sync(reset_test_snapshot)
                async with engine.begin() as connection:
                    await connection.run_sync(initialize)
            async with engine.begin() as connection:
                await connection.run_sync(initialize)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--roundtrip-test", action="store_true")
    asyncio.run(main(parser.parse_args().roundtrip_test))
