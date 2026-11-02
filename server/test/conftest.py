import pytest
from fastapi.testclient import TestClient

from database import init_db
from main import app


@pytest.fixture
def db():
    """A fresh seeded database with an empty tracking table."""
    conn = init_db()
    yield conn
    conn.close()


@pytest.fixture
def client():
    # Entering the context runs the lifespan, so every test gets a fresh database.
    with TestClient(app) as test_client:
        yield test_client
