"""
Database connection helpers for MacroPulse.

Uses a ThreadedConnectionPool (psycopg2) so the API layer reuses connections
instead of opening a new one per query — prevents connection exhaustion under load.

Pool is initialized lazily on first use and shared across the process lifetime.
"""

from __future__ import annotations

import contextlib
import logging
import threading
from typing import Generator

import psycopg2
import psycopg2.extras
import psycopg2.pool

from config.settings import get_settings

logger = logging.getLogger(__name__)

_pool: psycopg2.pool.ThreadedConnectionPool | None = None
_pool_lock = threading.Lock()

_POOL_MIN = 2
_POOL_MAX = 10


def _get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is not None:
        return _pool
    with _pool_lock:
        if _pool is None:
            settings = get_settings()
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=_POOL_MIN,
                maxconn=_POOL_MAX,
                dsn=settings.database_url,
            )
            logger.info("DB connection pool initialised (min=%d max=%d).", _POOL_MIN, _POOL_MAX)
    return _pool


def get_sync_connection() -> psycopg2.extensions.connection:
    """Borrow a connection from the pool. Caller must return it via pool.putconn()."""
    return _get_pool().getconn()


@contextlib.contextmanager
def get_sync_cursor(
    autocommit: bool = False,
) -> Generator[psycopg2.extras.RealDictCursor, None, None]:
    """Context-managed cursor with automatic commit / rollback and pool return."""
    pool = _get_pool()
    conn = pool.getconn()
    conn.autocommit = autocommit
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            yield cur
            if not autocommit:
                conn.commit()
    except Exception:
        if not autocommit:
            try:
                conn.rollback()
            except Exception:
                pass
        raise
    finally:
        pool.putconn(conn)


def close_pool() -> None:
    """Drain and close the connection pool (called on app shutdown)."""
    global _pool
    if _pool is not None:
        _pool.closeall()
        _pool = None
        logger.info("DB connection pool closed.")


def init_schema() -> None:
    """Execute the DDL schema against the connected database."""
    from pathlib import Path

    schema_path = Path(__file__).parent / "schema.sql"
    sql = schema_path.read_text()
    with get_sync_cursor(autocommit=True) as cur:
        cur.execute(sql)
    logger.info("Database schema initialised.")
