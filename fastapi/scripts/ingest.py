"""
Chunk ingestion script — run once after migrate:fresh --seed.

Reads all lessons from PostgreSQL, splits content into chunks,
embeds with bge-m3, and upserts into pmp_chunks.

Usage (from fastapi/ directory):
    uv run python scripts/ingest.py

Or inside Docker:
    docker exec -it tarteel_fastapi uv run python scripts/ingest.py
"""

import asyncio
import json
import re
import sys

import asyncpg
import httpx

# ---------------------------------------------------------------------------
# Config (read directly from env — no Pydantic dependency for this script)
# ---------------------------------------------------------------------------
import os
from pathlib import Path

# Load .env if present
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ["DATABASE_URL"]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "bge-m3"
CHUNK_SIZE_WORDS = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 8  # chunks per embed call


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def split_into_chunks(text: str, size: int = CHUNK_SIZE_WORDS, overlap: int = CHUNK_OVERLAP_WORDS) -> list[str]:
    """Split text into overlapping word-count chunks."""
    words = text.split()
    if not words:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start += size - overlap
    return chunks


# ---------------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------------
async def embed_batch(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    response = await client.post(
        f"{OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=120.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"]


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------
async def fetch_lessons(conn: asyncpg.Connection) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT l.id, l.title, l.content, l.slug,
               d.slug AS domain_slug
        FROM lessons l
        JOIN domains d ON d.id = l.domain_id
        WHERE l.content IS NOT NULL AND l.content != ''
        ORDER BY l.id
        """
    )
    return [dict(r) for r in rows]


async def upsert_chunks(
    conn: asyncpg.Connection,
    lesson_id: int,
    domain_slug: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    """Delete existing chunks for this lesson, insert fresh ones. Returns count inserted."""
    await conn.execute("DELETE FROM pmp_chunks WHERE lesson_id = $1", lesson_id)

    inserted = 0
    for idx, (content, embedding) in enumerate(zip(chunks, embeddings)):
        vector_literal = f"[{','.join(str(x) for x in embedding)}]"
        metadata = json.dumps({"domain": domain_slug, "lesson_id": lesson_id})
        await conn.execute(
            """
            INSERT INTO pmp_chunks (lesson_id, content, metadata, chunk_index, created_at, updated_at)
            VALUES ($1, $2, $3::jsonb, $4, NOW(), NOW())
            """,
            lesson_id,
            content,
            metadata,
            idx,
        )
        # Update embedding separately (asyncpg can't bind vector type inline)
        await conn.execute(
            f"UPDATE pmp_chunks SET embedding = '{vector_literal}'::vector "
            "WHERE lesson_id = $1 AND chunk_index = $2",
            lesson_id,
            idx,
        )
        inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main() -> None:
    print(f"Connecting to {DATABASE_URL[:40]}...")
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=3)

    async with httpx.AsyncClient() as client:
        # Quick Ollama health check
        try:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            r.raise_for_status()
            print(f"Ollama OK at {OLLAMA_BASE_URL}")
        except Exception as e:
            print(f"ERROR: Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}")
            print("Make sure Ollama is running and bge-m3 is pulled.")
            sys.exit(1)

        async with pool.acquire() as conn:
            lessons = await fetch_lessons(conn)
            print(f"Found {len(lessons)} lessons to ingest\n")

            total_chunks = 0
            for lesson in lessons:
                lesson_id = lesson["id"]
                domain_slug = lesson["domain_slug"]
                content = lesson["content"] or ""

                chunks = split_into_chunks(content)
                if not chunks:
                    print(f"  [{lesson_id}] {lesson['title'][:40]} — skipped (empty content)")
                    continue

                print(f"  [{lesson_id}] {lesson['title'][:40]} — {len(chunks)} chunks", end="", flush=True)

                # Embed in batches
                all_embeddings: list[list[float]] = []
                for i in range(0, len(chunks), BATCH_SIZE):
                    batch = chunks[i : i + BATCH_SIZE]
                    embeddings = await embed_batch(batch, client)
                    all_embeddings.extend(embeddings)
                    print(".", end="", flush=True)

                inserted = await upsert_chunks(conn, lesson_id, domain_slug, chunks, all_embeddings)
                total_chunks += inserted
                print(f" ✓")

    await pool.close()
    print(f"\nDone. Inserted {total_chunks} chunks across {len(lessons)} lessons.")


if __name__ == "__main__":
    asyncio.run(main())
