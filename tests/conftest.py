"""Pytest configuration and fixtures for Recruiter Workflow API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from recruiter_workflow.database import Base, get_db

# Import all models so they register with Base.metadata
import recruiter_workflow.models.job_description  # noqa: F401
import recruiter_workflow.models.resume  # noqa: F401
import recruiter_workflow.models.candidate  # noqa: F401
import recruiter_workflow.models.recruitment_stage  # noqa: F401

# Use in-memory SQLite with StaticPool so all connections share the same DB
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


def override_get_db():
    """Override the get_db dependency for testing."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a fresh database for each test."""
    Base.metadata.create_all(bind=test_engine)
    yield
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(test_db):
    """Create a test client that uses the test database."""
    from recruiter_workflow.main import create_app

    app = create_app()
    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c