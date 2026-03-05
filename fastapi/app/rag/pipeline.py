import asyncio
import json
from typing import AsyncGenerator

import httpx

from app.cache import make_cache_key, set_cached_response, write_db_cache
from app.database import fetch_chunks_by_ids, get_connection
from app.prompts import build_user_message, get_system_prompt, should_use_think_mode
from app.rag.embeddings import embed_query
from app.rag.generator import assemble_context, format_chunk_with_source, generate_full, generate_stream
from app.rag.reranker import rerank
from app.rag.retrieval import retrieve
from app.schemas import Chunk, ExplainRequest


async def _run_rag_stages(
    request: ExplainRequest,
    client: httpx.AsyncClient,
) -> tuple[list[Chunk], str, str]:
    """
    Shared RAG stages 1-5 for both streaming and non-streaming modes.
    Returns (top_chunks, user_message, system_prompt).
    """
    # Stage 1: Metadata routing — domain + lesson_id from request, no LLM
    domain = request.domain
    lesson_id = request.lesson_id

    # Free-form tutor queries (no lesson) search all domains for maximum recall
    search_all_domains = lesson_id is None

    # Wider retrieval window when searching all domains
    retrieval_limit = 40 if search_all_domains else 25

    # Stage 2: Embed the question stem
    query_embedding = await embed_query(request.question_stem, client)

    # Stage 3: BM25 + vector retrieval → RRF fusion
    async with get_connection() as conn:
        rrf_results = await retrieve(
            query=request.question_stem,
            embedding=query_embedding,
            domain=domain,
            lesson_id=lesson_id,
            conn=conn,
            retrieval_limit=retrieval_limit,
            search_all_domains=search_all_domains,
        )

    # Stage 4: Fetch full chunk rows, re-sort to preserve RRF ranking order
    chunk_ids_ranked = [chunk_id for chunk_id, _ in rrf_results]
    raw_chunks = await fetch_chunks_by_ids(chunk_ids_ranked)
    id_to_chunk = {row["id"]: Chunk(**row) for row in raw_chunks}
    chunks_ordered = [id_to_chunk[cid] for cid in chunk_ids_ranked if cid in id_to_chunk]

    # Stage 5: Rerank → top 5, assemble context with source citations
    reranked = await rerank(query=request.question_stem, chunks=chunks_ordered, client=client, top_k=5)
    top_chunks = [chunk for chunk, _ in reranked]

    # Format each chunk with its source/page prefix for citation
    chunk_texts = [
        format_chunk_with_source(c.content, c.metadata if isinstance(c.metadata, dict) else {})
        for c in top_chunks
    ]
    selected_texts, _ = assemble_context(chunk_texts)

    system_prompt = get_system_prompt(request.question_stem)
    use_think = should_use_think_mode(request.question_stem)
    user_message = build_user_message(
        question_stem=request.question_stem,
        selected_option=request.selected_option,
        context_chunks=selected_texts,
        use_think=use_think,
    )

    return top_chunks, user_message, system_prompt


async def run_pipeline_streaming(
    request: ExplainRequest,
    client: httpx.AsyncClient,
) -> AsyncGenerator[str, None]:
    """
    Full RAG pipeline for SSE streaming mode.
    Yields SSE-formatted strings. Writes cache after all tokens emitted.
    """
    top_chunks, user_message, system_prompt = await _run_rag_stages(request, client)
    top_chunk_ids = [c.id for c in top_chunks]
    cache_key = make_cache_key(request.question_id, request.selected_option, request.question_stem)

    full_response_parts: list[str] = []

    async for token in generate_stream(system_prompt, user_message, client):
        full_response_parts.append(token)
        yield f"data: {json.dumps(token, ensure_ascii=False)}\n\n"

    yield "data: [DONE]\n\n"

    # Write cache after generation completes
    full_response = "".join(full_response_parts)
    async with get_connection() as conn:
        await asyncio.gather(
            set_cached_response(cache_key, full_response, top_chunk_ids),
            write_db_cache(conn, cache_key, full_response, top_chunk_ids),
        )


async def run_pipeline_full(
    request: ExplainRequest,
    client: httpx.AsyncClient,
) -> tuple[str, list[int], str]:
    """
    Full RAG pipeline for non-streaming (background job) mode.
    Returns (explanation, chunk_ids, cache_key).
    """
    top_chunks, user_message, system_prompt = await _run_rag_stages(request, client)
    top_chunk_ids = [c.id for c in top_chunks]
    cache_key = make_cache_key(request.question_id, request.selected_option, request.question_stem)

    explanation = await generate_full(system_prompt, user_message, client)

    async with get_connection() as conn:
        await asyncio.gather(
            set_cached_response(cache_key, explanation, top_chunk_ids),
            write_db_cache(conn, cache_key, explanation, top_chunk_ids),
        )

    return explanation, top_chunk_ids, cache_key
