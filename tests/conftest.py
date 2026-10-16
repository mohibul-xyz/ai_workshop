import os
from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Connection, create_engine
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://taskhub:taskhub@db:5432/taskhub_test"
)


@pytest.fixture(scope="session")
def connection() -> Iterator[Connection]:
    os.environ["ALEMBIC_DATABASE_URL"] = TEST_DATABASE_URL
    command.upgrade(Config("alembic.ini"), "head")
    engine = create_engine(TEST_DATABASE_URL)
    with engine.connect() as conn:
        yield conn
    engine.dispose()


@pytest.fixture
def session(connection: Connection) -> Iterator[Session]:
    """Run each test in a rolled-back transaction; service commits become savepoints."""
    outer = connection.begin()
    db = Session(bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False)
    try:
        yield db
    finally:
        db.close()
        outer.rollback()


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def project_id(client: TestClient) -> int:
    resp = client.post("/api/v1/projects", json={"name": "Demo"})
    assert resp.status_code == 201
    return int(resp.json()["id"])
