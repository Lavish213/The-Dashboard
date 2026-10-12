import pytest
from sqlalchemy.engine import make_url


def validate_disposable_database(dsn: str) -> None:
    if not dsn:
        raise pytest.UsageError("TEST_DATABASE_URL must name a disposable loopback database ending in _test")
    url = make_url(dsn)
    if url.drivername != "postgresql+asyncpg" or url.host not in {"localhost", "127.0.0.1", "::1", "postgres"} or not url.database or not url.database.endswith("_test"):
        raise pytest.UsageError("Refusing schema reset outside the explicit disposable test database")
