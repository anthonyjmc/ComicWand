"""Database engine and session dependency helpers."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()


def _normalize_async_database_url(database_url: str) -> str:
    """Normalize asyncpg DSN options for SQLAlchemy async engine.

    Supabase URLs commonly use `sslmode=require` (libpq style). asyncpg expects `ssl=...`.
    """
    needs_sslmode_normalization = "sslmode=" in database_url
    if not needs_sslmode_normalization:
        return database_url

    parts = urlsplit(database_url)
    query_items = dict(parse_qsl(parts.query, keep_blank_values=True))

    sslmode = query_items.pop("sslmode", "").strip().lower()
    if sslmode in {"require", "verify-ca", "verify-full"}:
        query_items["ssl"] = "require"
    elif sslmode in {"disable", "allow", "prefer"}:
        query_items["ssl"] = sslmode

    normalized_query = urlencode(query_items)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, normalized_query, parts.fragment))


normalized_database_url = _normalize_async_database_url(settings.database_url)
engine_connect_args: dict[str, object] = {}
if "+asyncpg" in normalized_database_url:
    # PgBouncer in transaction/statement mode is incompatible with asyncpg prepared statement cache.
    engine_connect_args["statement_cache_size"] = 0

engine = create_async_engine(
    normalized_database_url,
    future=True,
    pool_pre_ping=True,
    connect_args=engine_connect_args,
)
SessionFactory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session with automatic cleanup."""
    async with SessionFactory() as session:
        yield session
