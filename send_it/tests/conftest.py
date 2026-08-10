import os

import pytest
from sqlmodel import SQLModel, Session, create_engine
from fastapi.testclient import TestClient

from main import app
from database.session import get_session


test_engine = create_engine(
    "sqlite:///./test.db",
    connect_args={"check_same_thread": False},
)


def get_test_session():
    with Session(test_engine) as session:
        yield session


@pytest.fixture
def client():
    # Tell the application we are running tests
    os.environ["TESTING"] = "1"

    # Use SQLite instead of PostgreSQL
    app.dependency_overrides[get_session] = get_test_session

    # Create test tables
    SQLModel.metadata.create_all(test_engine)

    with TestClient(app, raise_server_exceptions=True) as test_client:
        yield test_client

    # Clean up
    SQLModel.metadata.drop_all(test_engine)
    app.dependency_overrides.clear()

    # Remove testing mode
    os.environ.pop("TESTING", None)