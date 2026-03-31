"""
Database connection helpers for MacroPulse.

Uses an asyncpg connection pool so async route handlers can acquire connections
without blocking the event loop — replaces the old psycopg2 ThreadedConnectionPool.

Pool is initialised at application startup via init_pool() and shared across the
process lifetime via the module-level _pool variable.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
from typing import AsyncGenerator

import asyncpg

logger = logging.getLogger(__name__)

_pool: asyncpg.Pool | None = None

_POOL_MIN = int(os.getenv("DB_POOL_MIN", "5"))
_POOL_MAX = int(os.getenv("DB_POOL_MAX", "20"))
_CMD_TIMEOUT = 30


async def _init_connection(conn: asyncpg.Connection) -> None:
    """Register JSONB codec so dicts/lists round-trip transparently."""
    await conn.set_type_codec(
        "jsonb",
        encoder=json.dumps,
        decoder=json.loads,
        schema="pg_catalog",
    )


async def init_pool(dsn: str) -> None:
    """Create the asyncpg connection pool and store it in the module-level _pool.

    Must be called once at application startup before any request is served.
    """
    global _pool
    _pool = await asyncpg.create_pool(
        dsn,
        min_size=_POOL_MIN,
        max_size=_POOL_MAX,
        command_timeout=_CMD_TIMEOUT,
        init=_init_connection,
    )
    logger.info(
        "DB connection pool initialised (min=%d max=%d timeout=%ds).",
        _POOL_MIN,
        _POOL_MAX,
        _CMD_TIMEOUT,
    )


async def close_pool() -> None:
    """Drain and close the connection pool (called on app shutdown)."""
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None
        logger.info("DB connection pool closed.")


@contextlib.asynccontextmanager
async def get_db_conn() -> AsyncGenerator[asyncpg.Connection, None]:
    """Async context manager that yields an asyncpg connection from the pool.

    Usage::

        async with get_db_conn() as conn:
            row = await conn.fetchrow("SELECT * FROM table WHERE id = $1", id)
    """
    assert _pool is not None, "Pool not initialised — call init_pool() first"
    async with _pool.acquire() as conn:
        yield conn

