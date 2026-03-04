import json
from typing import AsyncGenerator

import httpx
from fastapi import HTTPException, status

from app.config import settings

GENERATOR_MODEL = "qwen3:8b"
MAX_CONTEXT_TOKENS = 3800
CHARS_PER_TOKEN = 4


async def generate_stream(
    system_prompt: str,
    user_message: str,
    client: httpx.AsyncClient,
) -> AsyncGenerator[str, None]:
    """Stream token deltas from Ollama /api/chat. Yields raw text chunks."""
    payload = {
        "model": GENERATOR_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "options": {
            "temperature": 0.3,
            "top_p": 0.9,
            "num_ctx": 4096,
        },
    }
    try:
        async with client.stream(
            "POST",
            f"{settings.OLLAMA_BASE_URL}/api/chat",
            json=payload,
            timeout=120.0,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    delta = data.get("message", {}).get("content", "")
                    if delta:
                        yield delta
                    if data.get("done"):
                        break
                except (json.JSONDecodeError, KeyError):
                    continue
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Ollama unavailable: {exc}",
        )


async def generate_full(
    system_prompt: str,
    user_message: str,
    client: httpx.AsyncClient,
) -> str:
    """Non-streaming wrapper. Collects all tokens into a single string."""
    parts: list[str] = []
    async for chunk in generate_stream(system_prompt, user_message, client):
        parts.append(chunk)
    return "".join(parts)


def estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def assemble_context(
    chunks: list[str],
    max_tokens: int = MAX_CONTEXT_TOKENS,
) -> tuple[list[str], int]:
    """Greedily add chunks until token budget exhausted. Returns (selected, tokens_used)."""
    selected: list[str] = []
    used = 0
    for chunk in chunks:
        chunk_tokens = estimate_tokens(chunk)
        if used + chunk_tokens > max_tokens:
            break
        selected.append(chunk)
        used += chunk_tokens
    return selected, used
