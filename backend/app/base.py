"""
base.py — Declarative Base class shared by all ORM models and Alembic.

Kept as a standalone module so that both the application (database.py) and
Alembic (alembic/env.py) can import the shared Base without pulling in each
other's dependencies.  The engine and session factory live in database.py.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase


# Global naming convention for all SQLAlchemy-generated constraints/indexes.
# This prevents Alembic from generating unnamed constraints (name=None), which
# can break downgrade operations on PostgreSQL when DROP CONSTRAINT requires a name.
NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_name)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Shared declarative base for every SQLAlchemy ORM model in CampaignPulse.

    All 14 models in models.py inherit from this class.  SQLAlchemy collects
    their table definitions in Base.metadata, which Alembic reads at migration
    time to generate CREATE / ALTER TABLE statements automatically.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
