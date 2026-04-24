"""
conftest.py — Shared pytest fixtures for CampaignPulse backend tests.

Design decisions
────────────────
1. Real PostgreSQL test database
   SQLite is avoided because the ORM models use PostgreSQL-specific types
   (JSONB, UUID with gen_random_uuid() server defaults, TIMESTAMP WITH TIME ZONE).
   A dedicated `campaign_pulse_test_db` database is created automatically on
   first run and dropped/recreated on each test session.

2. Per-test isolation via table truncation
   After every test, an autouse fixture deletes all rows from every table in
   reverse topological order (children before parents), so each test starts
   with a completely empty database.

3. Shared session per test
   The `db` fixture and the `client` fixture share the same SQLAlchemy Session
   object.  The client fixture overrides FastAPI's `get_db` dependency to yield
   that same session, so both test assertions and route handlers operate on
   identical committed state.

4. Log suppression
   logging.disable(logging.CRITICAL) is called at module import time, before
   any application logger is configured, so zero log output appears in the
   test terminal.
"""

import logging
import os
from urllib.parse import urlparse, urlunparse

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# ── Suppress ALL application logs before any module is imported ────────────
logging.disable(logging.CRITICAL)

# ── Load .env ──────────────────────────────────────────────────────────────
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH, override=True)

# ── Derive test database URL ───────────────────────────────────────────────
_DB_URL: str = os.environ.get("DATABASE_URL", "")
if not _DB_URL:
    raise RuntimeError("DATABASE_URL is not set in .env")

# Replace the production database name with the test database name.
_parsed = urlparse(_DB_URL)
_TEST_DB_NAME = "campaign_pulse_test_db"
TEST_DATABASE_URL: str = urlunparse(_parsed._replace(path=f"/{_TEST_DB_NAME}"))

# Admin URL points to the built-in `postgres` maintenance database so we can
# issue CREATE/DROP DATABASE statements outside any transaction.
ADMIN_DATABASE_URL: str = urlunparse(_parsed._replace(path="/postgres"))

# ── Late imports (after env is loaded) ────────────────────────────────────
from app.base import Base  # noqa: E402
from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402


# ===========================================================================
# Session-scoped: engine + schema bootstrap
# ===========================================================================


@pytest.fixture(scope="session")
def test_engine():
    """
    Create `campaign_pulse_test_db` if it does not already exist, build all
    tables from the ORM metadata, and yield the engine.  Tables are dropped
    after the entire test session completes.
    """
    # Create the test database if it doesn't exist.
    admin_engine = create_engine(
        ADMIN_DATABASE_URL,
        isolation_level="AUTOCOMMIT",
        poolclass=NullPool,
    )
    with admin_engine.connect() as conn:
        exists = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": _TEST_DB_NAME},
        ).fetchone()
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))
    admin_engine.dispose()

    # Connect to the test database and create all tables.
    engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
    Base.metadata.create_all(engine)
    yield engine

    # Teardown: drop all tables after the full session.
    Base.metadata.drop_all(engine)
    engine.dispose()


# ===========================================================================
# Function-scoped: per-test session + table cleanup
# ===========================================================================


@pytest.fixture
def db(test_engine):
    """
    Yield a fresh SQLAlchemy Session for a single test.

    The session is closed (and any uncommitted work rolled back) after the
    test finishes.  The `clean_tables` autouse fixture then truncates all
    rows so the next test starts with an empty database.
    """
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSession()
    yield session
    session.rollback()
    session.close()


@pytest.fixture(autouse=True)
def clean_tables(test_engine):
    """
    Delete all rows from every table after each test, in reverse topological
    order (children before parents) to satisfy foreign-key constraints.
    This fixture runs automatically for every test function.
    """
    yield  # run the test first
    with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())


# ===========================================================================
# Function-scoped: TestClient with overridden get_db
# ===========================================================================


@pytest.fixture
def client(db):
    """
    Return a Starlette TestClient whose `get_db` dependency is overridden to
    use the same `db` session as the test function itself.

    This means route handlers and test assertions operate on the same
    session — any data committed by a route handler is immediately visible
    to subsequent `db.query(...)` calls in the test body.
    """

    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    # raise_server_exceptions=False returns the HTTP error response instead of
    # re-raising the exception, which is what we want for 4xx/5xx assertions.
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c

    app.dependency_overrides.clear()
