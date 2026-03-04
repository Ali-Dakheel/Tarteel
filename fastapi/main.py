from contextlib import asynccontextmanager
from typing import AsyncGenerator

import httpx
from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from app.auth import verify_internal_key
from app.cache import close_redis, create_redis, get_cached_response, make_cache_key
from app.config import settings
from app.database import close_pool, create_pool
from app.rag.pipeline import run_pipeline_full, run_pipeline_streaming
from app.schemas import ExplainRequest, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await create_pool()
    await create_redis()
    app.state.client = httpx.AsyncClient(timeout=httpx.Timeout(120.0))
    yield
    await app.state.client.aclose()
    await close_pool()
    await close_redis()


app = FastAPI(
    title="Tarteel AI Microservice",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "local" else None,
    redoc_url=None,
    openapi_url="/openapi.json" if settings.ENVIRONMENT == "local" else None,
)


async def _cached_sse(explanation: str) -> AsyncGenerator[str, None]:
    yield f"data: {explanation}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/explain", dependencies=[Depends(verify_internal_key)])
async def explain(request: Request, body: ExplainRequest):
    """
    RAG explanation endpoint. Two modes detected via Accept header:
    - text/event-stream → SSE streaming (TutorController live chat)
    - anything else     → full JSON body (GenerateAiExplanationJob background)
    """
    client = request.app.state.client
    cache_key = make_cache_key(body.question_id, body.selected_option)
    cached = await get_cached_response(cache_key)
    is_streaming = "text/event-stream" in request.headers.get("accept", "")

    if cached and is_streaming:
        return StreamingResponse(
            _cached_sse(cached),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )
    if cached:
        return JSONResponse({"explanation": cached, "chunk_ids": [], "cache_key": cache_key})
    if is_streaming:
        return StreamingResponse(
            run_pipeline_streaming(body, client),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    explanation, chunk_ids, key = await run_pipeline_full(body, client)
    return JSONResponse({"explanation": explanation, "chunk_ids": chunk_ids, "cache_key": key})


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", ollama=True, postgres=True, redis=True)
