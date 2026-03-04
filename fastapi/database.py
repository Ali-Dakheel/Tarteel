from contextlib import asynccontextmanager
from typing import AsyncGenerator

import asyncpg

from config import settings

_pool: asyncpg.Pool | None = None


async def create_pool() -> None:
    global _pool
    _pool = await asyncpg.create_pool(
        dsn=settings.DATABASE_URL,
        min_size=2,
        max_size=10,
        command_timeout=30,
    )


async def close_pool() -> None:
    if _pool:
        await _pool.close()


@asynccontextmanager
async def get_connection() -> AsyncGenerator[asyncpg.Connection, None]:
    async with _pool.acquire() as conn:
        yield conn


async def fetch_chunks_by_ids(ids: list[int]) -> list[dict]:
    """Fetch full pmp_chunks rows by PK list. Returns rows in arbitrary order — caller must re-sort."""
    if not ids:
        return []
    async with get_connection() as conn:
        rows = await conn.fetch(
            "SELECT id, lesson_id, content, metadata, chunk_index "
            "FROM pmp_chunks WHERE id = ANY($1::bigint[])",
            ids,
        )
    return [dict(r) for r in rows]
