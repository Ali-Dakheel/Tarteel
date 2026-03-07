import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def generate_hypothesis(question: str, client: httpx.AsyncClient) -> str:
    """
    HyDE — Hypothetical Document Embedding.

    Generate a short hypothetical textbook passage that would answer the question,
    then embed that passage instead of the raw question for vector search.

    This bridges the semantic gap between short question vectors and long declarative
    book text in embedding space, dramatically improving recall for factual lookups.

    BM25 still uses the original question (exact keywords work fine as-is).
    Falls back to the original question on any error to avoid breaking the pipeline.
    """
    prompt = (
        f"Write one short paragraph (2-3 sentences) from a PMP reference book that directly "
        f"answers: '{question}'. "
        "Output ONLY the paragraph text, no preamble, no markdown. /no_think"
    )
    try:
        r = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "qwen3:8b",
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"num_predict": 150, "temperature": 0.2},
            },
            timeout=30.0,
        )
        r.raise_for_status()
        hypothesis = r.json().get("response", "").strip()
        return hypothesis if hypothesis else question
    except Exception as e:
        logger.warning("HyDE failed, falling back to original question: %s", e)
        return question
