from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg_pool import AsyncConnectionPool

from sts2.config import settings

_SCHEMA = (Path(__file__).parent.parent.parent / "schema.sql").read_text()

_pool: AsyncConnectionPool | None = None


def get_pool() -> AsyncConnectionPool:
    assert _pool is not None, "pool is not initialised — call open_pool() first"
    return _pool


async def init_db() -> None:
    """Run schema.sql against the database. Safe to call on every startup."""
    async with await psycopg.AsyncConnection.connect(
        str(settings.database_url), autocommit=True
    ) as conn:
        await conn.execute(_SCHEMA)


async def open_pool() -> None:
    global _pool
    _pool = AsyncConnectionPool(str(settings.database_url))


async def close_pool() -> None:
    if _pool is not None:
        await _pool.close()
