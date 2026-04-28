"""Alembic environment for sync migrations (Supabase/Postgres)."""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine.url import make_url

from app.core.config import get_settings

# Alembic Config object, provides access to the values within alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Autogenerate support is optional: this project ships explicit migrations.
target_metadata = None


def _migration_engine_url() -> str:
    """Build a sync SQLAlchemy URL for Alembic DDL.

    The FastAPI app uses async SQLAlchemy with asyncpg, but Alembic runs synchronously.
    We map `postgresql+asyncpg` -> `postgresql+pg8000` which works well with managed Postgres (Supabase).
    """
    url = make_url(get_settings().database_url)
    if url.drivername in {"postgresql+asyncpg", "postgres+asyncpg"}:
        url = url.set(drivername="postgresql+pg8000")
    return url.render_as_string(hide_password=False)


def run_migrations_offline() -> None:
    url = _migration_engine_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(_migration_engine_url(), poolclass=pool.NullPool)

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
