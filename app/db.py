"""asyncpg connection pool + helpers."""
from __future__ import annotations

import asyncpg
from asyncpg.pool import Pool

from app.config import settings

_pool: Pool | None = None


async def init_pool() -> Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.database_url,
            min_size=1,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> Pool:
    if _pool is None:
        raise RuntimeError("DB pool not initialized. Call init_pool() at startup.")
    return _pool
