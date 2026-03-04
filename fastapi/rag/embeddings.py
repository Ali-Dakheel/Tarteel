import httpx

from config import settings

EMBEDDING_MODEL = "bge-m3"
EMBEDDING_DIM = 1024


async def embed_query(text: str, client: httpx.AsyncClient) -> list[float]:
    """Call Ollama /api/embed with bge-m3. Returns a 1024-dim float list."""
    response = await client.post(
        f"{settings.OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": text},
        timeout=30.0,
    )
    response.raise_for_status()
    data = response.json()
    # Ollama /api/embed: {"embeddings": [[...1024 floats...]]}
    return data["embeddings"][0]


async def embed_batch(texts: list[str], client: httpx.AsyncClient) -> list[list[float]]:
    """Batch embed multiple texts. Used during chunk ingestion, not at query time."""
    response = await client.post(
        f"{settings.OLLAMA_BASE_URL}/api/embed",
        json={"model": EMBEDDING_MODEL, "input": texts},
        timeout=60.0,
    )
    response.raise_for_status()
    return response.json()["embeddings"]
