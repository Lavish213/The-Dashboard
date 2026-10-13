import asyncio
import os

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

from db.base import Base
from models.registry import load_all_models
from testing.database import validate_disposable_database


def verify(connection):
    load_all_models()
    context = MigrationContext.configure(connection, opts={"compare_type": True})
    differences = compare_metadata(context, Base.metadata)
    if differences:
        raise AssertionError(f"Migration/model drift: {differences}")
    expected_enums = {}
    for table in Base.metadata.tables.values():
        for column in table.columns:
            value = column.type
            if getattr(value, "native_enum", False):
                expected_enums[value.name] = list(value.enums)
    actual_enums = {item["name"]: item["labels"] for item in inspect(connection).get_enums()}
    for name, labels in expected_enums.items():
        if actual_enums.get(name) != labels:
            raise AssertionError(f"Enum drift: {name}")
    print(f"Verified {len(Base.metadata.tables)} migrated tables and {len(expected_enums)} enums against all registered models")


async def main():
    url = os.environ.get("TEST_DATABASE_URL", "")
    validate_disposable_database(url)
    engine = create_async_engine(url)
    try:
        async with engine.connect() as connection:
            await connection.run_sync(verify)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
