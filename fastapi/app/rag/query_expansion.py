"""
Multi-query expansion for RAG retrieval.

Generates 2 alternative phrasings of the user's question using Qwen3.
These additional queries are embedded separately and merged via RRF,
improving recall especially for Arabic/English code-switching queries.
"""

from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


async def expand_query(question: str, client: httpx.AsyncClient) -> list[str]:
    """
    Return [original_question, rephrasing_1, rephrasing_2].
    Falls back to [original_question] on any error — never blocks retrieval.

    For Arabic questions, rewrites include an English translation so that
    the English-language knowledge base is reachable via semantic similarity.
    """
    prompt = (
        "Rewrite the following PMP exam question in 2 alternative ways that preserve "
        "the meaning but use different wording and PMP terminology. "
        "If the question is in Arabic, write one Arabic rewrite and one English translation. "
        "Output only the 2 rewrites, one per line, no numbering, no preamble, no explanation.\n\n"
        f"Question: {question}"
    )
    try:
        r = await client.post(
            f"{settings.OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "qwen3:8b",
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"num_predict": 150, "temperature": 0.3},
            },
            timeout=20.0,
        )
        r.raise_for_status()
        text = r.json().get("response", "").strip()
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        extras = lines[:2]
        return [question] + extras if extras else [question]
    except Exception as e:
        logger.warning("Query expansion failed, falling back to original question: %s", e)
        return [question]
