"""
database.py — SQLAlchemy engine, session factory, and declarative base for CampaignPulse.

This module is the single entry-point for all database connectivity in the application.
Every other module that needs to talk to PostgreSQL imports from here.

Responsibilities:
  1. Load the DATABASE_URL connection string from the environment (.env file).
  2. Build the SQLAlchemy Engine — the low-level connection pool that holds open
     psycopg2 connections to PostgreSQL.
  3. Create a SessionLocal factory — each web request will open one Session from
     this factory, perform its work, then close it.
  4. Expose the shared Base class — all ORM models inherit from this so that
     Alembic's autogenerate can discover the full metadata graph.
  5. Provide get_db() — a FastAPI dependency that yields a database session per
     request and guarantees the session is closed even if an exception is raised.
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Base is defined in app.base and re-exported here for convenience.
# Callers can use either: from app.database import Base
#                     or: from app.base import Base
from app.base import Base  # noqa: F401

# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------

# Walk up from backend/app/ to find the repo-root .env file.
# Adjust the path if the .env lives elsewhere (e.g. inside backend/).
_ENV_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
load_dotenv(dotenv_path=_ENV_PATH)

# DATABASE_URL must follow the psycopg2 DSN format:
#   postgresql+psycopg2://user:password@host:port/dbname
# Example: postgresql+psycopg2://postgres:secret@localhost:5432/campaign_pulse_db
DATABASE_URL: str = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

# The engine manages a connection pool (default: 5 connections, overflow 10).
# pool_pre_ping=True tells SQLAlchemy to test each borrowed connection with a
# cheap "SELECT 1" before handing it to the application — this automatically
# recovers from dropped connections without surfacing errors to the caller.
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    # echo=True,  # Uncomment during development to log every SQL statement.
)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

# SessionLocal is a *factory* — calling SessionLocal() produces a new database
# session object.  autocommit=False means every write is inside a transaction
# that must be explicitly committed; autoflush=False prevents SQLAlchemy from
# silently issuing SQL during attribute access (safer for explicit control).
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def get_db():
    """
    Yield a SQLAlchemy Session for the duration of a single HTTP request.

    Usage in a FastAPI route:

        from app.database import get_db
        from sqlalchemy.orm import Session
        from fastapi import Depends

        @router.get("/example")
        def example(db: Session = Depends(get_db)):
            ...

    The try/finally block ensures the session is always closed — and the
    connection returned to the pool — regardless of whether the handler
    succeeded or raised an exception.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
