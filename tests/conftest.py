import os
# Must happen before any import that touches database.py
os.environ["EXPENSE_DB_URL"] = "sqlite://"
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from database import Base, get_db
from main import app
# ── In-memory engine shared across all test threads ───────────────────────────
TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)

def _override_get_db():
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = _override_get_db

@pytest.fixture(autouse=True)
def reset_db():
    """Drop and re-create all tables before every test."""
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    yield
    Base.metadata.drop_all(bind=TEST_ENGINE)

@pytest.fixture
def client():
    return TestClient(app)