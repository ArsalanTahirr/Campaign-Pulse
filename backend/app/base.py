"""
base.py — Declarative Base class shared by all ORM models and Alembic.

Kept as a standalone module so that both the application (database.py) and
Alembic (alembic/env.py) can import the shared Base without pulling in each
other's dependencies.  The engine and session factory live in database.py.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    Shared declarative base for every SQLAlchemy ORM model in CampaignPulse.

    All 14 models in models.py inherit from this class.  SQLAlchemy collects
    their table definitions in Base.metadata, which Alembic reads at migration
    time to generate CREATE / ALTER TABLE statements automatically.
    """
