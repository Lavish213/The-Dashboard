import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from api.main import app
    with TestClient(app) as c:
        yield c
