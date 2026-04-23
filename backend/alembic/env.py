import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# ---------------------------------------------------------------------------
# Make the `backend/` directory importable so that `from app.X import Y` works
# when Alembic is run from inside the backend/ folder.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load the .env file that lives two levels up (repo root) so DATABASE_URL is
# available before we try to connect.  python-dotenv is a no-op if the file
# doesn't exist, so this is safe in CI environments that inject vars directly.
from dotenv import load_dotenv

_ENV_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", ".env"
)
load_dotenv(dotenv_path=_ENV_PATH)

# Import the shared Base and all ORM models.
# Base lives in app.base (separate from the engine) so Alembic can read model
# metadata without requiring a live database connection at import time.
# Importing app.models is a side-effect import: it registers all 14 model
# classes onto Base.metadata, which --autogenerate diffs against the DB.
from app.base import Base  # noqa: E402
import app.models  # noqa: F401, E402

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override the sqlalchemy.url in alembic.ini with the value from the
# environment.  This keeps credentials out of version control entirely.
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise ValueError("DATABASE_URL is not set")

config.set_main_option("sqlalchemy.url", database_url)

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Point Alembic at our models' metadata so --autogenerate can diff the
# current schema against what the ORM describes.
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
