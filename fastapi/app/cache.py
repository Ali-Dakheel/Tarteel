import hashlib
import json
from datetime import datetime, timedelta, timezone

import asyncpg
import redis.asyncio as aioredis

from app.config import settings

_redis: aioredis.Redis | None = None

CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days


async def create_redis() -> None:
    global _redis
    _redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def close_redis() -> None:
    if _redis:
        await _redis.aclose()


def make_cache_key(question_id: int, selected_option: int) -> str:
    """Canonical cache key — must match Laravel's hash('sha256', $question_id.':'.$selected_option)."""
    raw = f"{question_id}:{selected_option}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_cached_response(cache_key: str) -> str | None:
    return await _redis.get(f"ai:explain:{cache_key}")


async def set_cached_response(
    cache_key: str,
    explanation: str,
    chunk_ids: list[int],
) -> None:
    await _redis.setex(f"ai:explain:{cache_key}", CACHE_TTL_SECONDS, explanation)


async def write_db_cache(
    conn: asyncpg.Connection,
    cache_key: str,
    explanation: str,
    chunk_ids: list[int],
) -> None:
    """Upsert into ai_response_cache. Safe to call multiple times — idempotent via ON CONFLICT."""
    # expires_at column is `timestamp` (no timezone) — must use naive datetime
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(seconds=CACHE_TTL_SECONDS)
    await conn.execute(
        """
        INSERT INTO ai_response_cache
            (query_hash, response, retrieved_chunk_ids, expires_at, created_at, updated_at)
        VALUES ($1, $2, $3::jsonb, $4, NOW(), NOW())
        ON CONFLICT (query_hash) DO UPDATE SET
            response = EXCLUDED.response,
            retrieved_chunk_ids = EXCLUDED.retrieved_chunk_ids,
            expires_at = EXCLUDED.expires_at,
            updated_at = NOW()
        """,
        cache_key,
        explanation,
        json.dumps(chunk_ids),
        expires_at,
    )
