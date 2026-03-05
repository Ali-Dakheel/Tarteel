import asyncio

import asyncpg


async def bm25_search(
    query: str,
    domain: str,
    lesson_id: int | None,
    limit: int,
    conn: asyncpg.Connection,
    search_all_domains: bool = False,
) -> list[tuple[int, float]]:
    """BM25 via PostgreSQL FTS. Returns (chunk_id, rank) tuples ordered by rank DESC."""
    if lesson_id is not None:
        rows = await conn.fetch(
            """
            SELECT id, ts_rank_cd(
                to_tsvector('english', content),
                websearch_to_tsquery('english', $1),
                32
            ) AS rank
            FROM pmp_chunks
            WHERE
                to_tsvector('english', content) @@ websearch_to_tsquery('english', $1)
                AND metadata->>'domain' = $2
                AND lesson_id = $3
            ORDER BY rank DESC
            LIMIT $4
            """,
            query, domain, lesson_id, limit,
        )
    elif search_all_domains:
        # Free-form tutor query — search across all domains for maximum recall
        rows = await conn.fetch(
            """
            SELECT id, ts_rank_cd(
                to_tsvector('english', content),
                websearch_to_tsquery('english', $1),
                32
            ) AS rank
            FROM pmp_chunks
            WHERE
                to_tsvector('english', content) @@ websearch_to_tsquery('english', $1)
            ORDER BY rank DESC
            LIMIT $2
            """,
            query, limit,
        )
    else:
        rows = await conn.fetch(
            """
            SELECT id, ts_rank_cd(
                to_tsvector('english', content),
                websearch_to_tsquery('english', $1),
                32
            ) AS rank
            FROM pmp_chunks
            WHERE
                to_tsvector('english', content) @@ websearch_to_tsquery('english', $1)
                AND metadata->>'domain' = $2
            ORDER BY rank DESC
            LIMIT $3
            """,
            query, domain, limit,
        )
    return [(row["id"], float(row["rank"])) for row in rows]


async def vector_search(
    embedding: list[float],
    domain: str,
    lesson_id: int | None,
    limit: int,
    conn: asyncpg.Connection,
    search_all_domains: bool = False,
) -> list[tuple[int, float]]:
    """pgvector cosine similarity search. Returns (chunk_id, distance) tuples ordered ASC."""
    # asyncpg can't bind Python list to vector type directly — format as literal string
    vector_literal = f"[{','.join(str(x) for x in embedding)}]"

    if lesson_id is not None:
        rows = await conn.fetch(
            f"""
            SELECT id, (embedding <=> '{vector_literal}'::vector) AS distance
            FROM pmp_chunks
            WHERE
                metadata->>'domain' = $1
                AND lesson_id = $2
                AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT $3
            """,
            domain, lesson_id, limit,
        )
    elif search_all_domains:
        # Free-form tutor query — search across all domains for maximum recall
        rows = await conn.fetch(
            f"""
            SELECT id, (embedding <=> '{vector_literal}'::vector) AS distance
            FROM pmp_chunks
            WHERE
                embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT $1
            """,
            limit,
        )
    else:
        rows = await conn.fetch(
            f"""
            SELECT id, (embedding <=> '{vector_literal}'::vector) AS distance
            FROM pmp_chunks
            WHERE
                metadata->>'domain' = $1
                AND embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT $2
            """,
            domain, limit,
        )
    return [(row["id"], float(row["distance"])) for row in rows]


def reciprocal_rank_fusion(
    bm25_results: list[tuple[int, float]],
    vector_results: list[tuple[int, float]],
    k: int = 60,
    top_n: int = 25,
) -> list[tuple[int, float]]:
    """Pure RRF fusion. score = Σ 1/(k + rank) for each list the chunk appears in."""
    scores: dict[int, float] = {}

    for rank, (chunk_id, _) in enumerate(bm25_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    for rank, (chunk_id, _) in enumerate(vector_results, start=1):
        scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank)

    sorted_results = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    return sorted_results[:top_n]


async def retrieve(
    query: str,
    embedding: list[float],
    domain: str,
    lesson_id: int | None,
    conn: asyncpg.Connection,
    retrieval_limit: int = 25,
    search_all_domains: bool = False,
) -> list[tuple[int, float]]:
    """Run BM25 + vector search sequentially (same connection), fuse with RRF."""
    # asyncpg connections don't support concurrent queries — run sequentially
    bm25_results = await bm25_search(query, domain, lesson_id, retrieval_limit, conn, search_all_domains)
    vector_results = await vector_search(embedding, domain, lesson_id, retrieval_limit, conn, search_all_domains)
    return reciprocal_rank_fusion(bm25_results, vector_results, top_n=retrieval_limit)
