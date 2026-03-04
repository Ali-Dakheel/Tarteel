import asyncio
import re

import httpx

from app.config import settings
from app.schemas import Chunk

RERANKER_MODEL = "qllama/bge-reranker-v2-m3"
RERANKER_CONCURRENCY = 4


async def score_passage(
    query: str,
    passage: str,
    client: httpx.AsyncClient,
) -> float:
    """Score a single query-passage pair. Returns 0.0–9.0 (higher = more relevant)."""
    prompt = (
        "Rate the relevance of the following passage to the query on a scale of 0 to 9.\n"
        "Output ONLY a single digit. Do not explain.\n\n"
        f"Query: {query}\n\n"
        f"Passage: {passage[:800]}\n\n"
        "Relevance score (0-9):"
    )
    try:
        response = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": RERANKER_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {"num_predict": 2, "temperature": 0},
            },
            timeout=15.0,
        )
        response.raise_for_status()
        text = response.json().get("response", "0").strip()
        match = re.search(r"\d", text)
        return float(match.group()) if match else 0.0
    except (httpx.HTTPError, ValueError, KeyError):
        # Graceful degradation: keep chunk with score 0 rather than failing the request
        return 0.0


async def rerank(
    query: str,
    chunks: list[Chunk],
    client: httpx.AsyncClient,
    top_k: int = 5,
) -> list[tuple[Chunk, float]]:
    """Rerank chunks with bounded concurrency. Returns top_k (Chunk, score) pairs."""
    semaphore = asyncio.Semaphore(RERANKER_CONCURRENCY)

    async def score_with_semaphore(chunk: Chunk) -> tuple[Chunk, float]:
        async with semaphore:
            score = await score_passage(query, chunk.content, client)
        return (chunk, score)

    scored = await asyncio.gather(*[score_with_semaphore(c) for c in chunks])
    scored_list = list(scored)
    scored_list.sort(key=lambda x: x[1], reverse=True)
    return scored_list[:top_k]
