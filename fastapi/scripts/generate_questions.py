"""
Book-grounded question generator.

Reads pmp_chunks from the DB (PDF chunks only, not lesson chunks),
asks Qwen3 to generate one PMP-style MCQ per chunk whose correct answer
is directly supported by that chunk's text.

The correct answer is grounded — not guessed. The source chunk IS the
explanation, so every question is self-verifying.

Usage (inside container):
    docker exec tarteel_fastapi uv run python scripts/generate_questions.py
    docker exec tarteel_fastapi uv run python scripts/generate_questions.py --limit 50
    docker exec tarteel_fastapi uv run python scripts/generate_questions.py --clear

After running, seed into DB:
    docker exec tarteel_fastapi uv run python scripts/seed_questions.py --clear
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg
import httpx

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())

DATABASE_URL = os.environ["DATABASE_URL"]
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://ollama:11434")
DATA_DIR = Path(__file__).parent.parent / "data"
OUTPUT_FILE = DATA_DIR / "questions.json"

CONCURRENCY = 3          # parallel Qwen3 calls at once — don't overwhelm Ollama
MIN_CHUNK_WORDS = 40     # skip very short chunks (headers, single sentences)
MAX_CHUNK_WORDS = 400    # skip huge chunks — too much context confuses the model

GENERATION_PROMPT = """\
You are a PMP exam question writer. Given a passage from an official PMP reference book,
write ONE multiple-choice exam question that tests understanding of the passage content.

Rules:
- The correct answer MUST be directly supported by the passage text (quote or paraphrase)
- The 3 wrong options must be plausible but clearly incorrect based on the passage
- Options must be A, B, C, D format — one sentence each, no "All of the above"
- Question stem must be one clear sentence ending with a question mark
- Output ONLY valid JSON, no explanation, no markdown, no preamble

Output format:
{
  "stem": "question text?",
  "options": ["option A text", "option B text", "option C text", "option D text"],
  "correct_option": 0,
  "explanation": "one sentence quoting or paraphrasing the passage that proves the answer"
}

Passage:
"""


# ---------------------------------------------------------------------------
# Domain detection (matches seed_questions.py logic)
# ---------------------------------------------------------------------------
_PEOPLE_KW = [
    "leadership", "team", "stakeholder", "conflict", "motivation", "coaching",
    "servant leader", "emotional intelligence", "collaboration", "communication",
    "negotiat", "influenc", "empower", "diversity", "inclusion", "tuckman",
    "forming", "storming", "norming", "performing",
]
_PROCESS_KW = [
    "scope", "schedule", "cost", "risk", "quality", "procurement", "wbs",
    "critical path", "earned value", "change control", "baseline", "charter",
    "initiating", "planning", "executing", "monitoring", "closing", "milestone",
    "estimate", "contingency", "sprint", "backlog", "iteration", "kanban",
]
_BE_KW = [
    "strategy", "governance", "portfolio", "program", "benefit", "roi",
    "compliance", "regulation", "pmo", "organizational", "business case",
    "value delivery", "strategic alignment", "enterprise",
]


def detect_domain(text: str) -> str:
    t = text.lower()
    people = sum(1 for kw in _PEOPLE_KW if kw in t)
    process = sum(1 for kw in _PROCESS_KW if kw in t)
    be = sum(1 for kw in _BE_KW if kw in t)
    scores = {"people": people, "process": process, "business-environment": be}
    return max(scores, key=lambda k: scores[k])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Generate one MCQ from a chunk
# ---------------------------------------------------------------------------
async def generate_question(
    chunk_id: int,
    content: str,
    metadata: dict,
    client: httpx.AsyncClient,
) -> dict | None:
    """Call Qwen3 to generate a single MCQ grounded in the chunk text."""

    # Strip the [Source | Section | Domain] prefix before sending to model
    chunk_text = re.sub(r"^\[.+?\]\n", "", content).strip()
    word_count = len(chunk_text.split())

    if word_count < MIN_CHUNK_WORDS or word_count > MAX_CHUNK_WORDS:
        return None

    prompt = GENERATION_PROMPT + chunk_text

    try:
        r = await client.post(
            f"{OLLAMA_BASE_URL}/api/generate",
            json={
                "model": "qwen3:8b",
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0.4,
                    "num_predict": 400,
                },
            },
            timeout=60.0,
        )
        r.raise_for_status()
        raw = r.json().get("response", "").strip()
    except Exception as e:
        print(f"  [chunk {chunk_id}] Ollama error: {e}")
        return None

    # Extract JSON from response (model sometimes adds extra text despite instructions)
    json_match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not json_match:
        print(f"  [chunk {chunk_id}] No JSON in response")
        return None

    try:
        q = json.loads(json_match.group())
    except json.JSONDecodeError as e:
        print(f"  [chunk {chunk_id}] JSON parse error: {e}")
        return None

    # Validate structure
    stem = q.get("stem", "").strip()
    options = q.get("options", [])
    correct_option = q.get("correct_option")
    explanation = q.get("explanation", "").strip()

    if (
        not stem
        or len(options) != 4
        or correct_option not in (0, 1, 2, 3)
        or not explanation
    ):
        print(f"  [chunk {chunk_id}] Invalid structure — skipping")
        return None

    source = metadata.get("source", "PMBOK")
    page = metadata.get("page")
    source_label = f"{source} p.{page}" if page else source

    return {
        "stem": stem,
        "options": [str(o).strip() for o in options],
        "correct_option": int(correct_option),
        "explanation": explanation,
        "difficulty": "medium",
        "domain": detect_domain(stem + " " + explanation),
        "source": source_label,
        "chunk_id": chunk_id,
    }


# ---------------------------------------------------------------------------
# Deduplication (same logic as base.py)
# ---------------------------------------------------------------------------
def deduplicate(questions: list[dict], threshold: float = 0.85) -> list[dict]:
    from difflib import SequenceMatcher

    kept: list[dict] = []
    for q in questions:
        stem = q["stem"].lower()
        is_dup = any(
            SequenceMatcher(None, stem, k["stem"].lower()).ratio() >= threshold
            for k in kept
        )
        if not is_dup:
            kept.append(q)
    return kept


# ---------------------------------------------------------------------------
# Fetch chunks from DB
# ---------------------------------------------------------------------------
async def fetch_chunks(limit: int | None) -> list[dict]:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        query = """
            SELECT id, content, metadata
            FROM pmp_chunks
            WHERE lesson_id IS NULL
            ORDER BY id
        """
        if limit:
            query += f" LIMIT {limit}"
        rows = await conn.fetch(query)
        return [dict(r) for r in rows]
    finally:
        await conn.close()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
async def main(limit: int | None, clear: bool) -> None:
    DATA_DIR.mkdir(exist_ok=True)

    # Optionally clear existing file
    if clear and OUTPUT_FILE.exists():
        OUTPUT_FILE.unlink()
        print("Cleared existing questions.json")

    # Load existing questions to avoid re-generating
    existing: list[dict] = []
    existing_chunk_ids: set[int] = set()
    if OUTPUT_FILE.exists():
        try:
            existing = json.loads(OUTPUT_FILE.read_text())
            existing_chunk_ids = {q["chunk_id"] for q in existing if "chunk_id" in q}
            print(f"Loaded {len(existing)} existing questions (will skip their chunks)")
        except Exception:
            pass

    print("Fetching chunks from DB...")
    chunks = await fetch_chunks(limit)
    # Skip chunks we already generated questions for
    chunks = [c for c in chunks if c["id"] not in existing_chunk_ids]
    print(f"Will process {len(chunks)} chunks (concurrency={CONCURRENCY})")

    results: list[dict] = []
    sem = asyncio.Semaphore(CONCURRENCY)

    async def process(chunk: dict) -> None:
        async with sem:
            metadata = chunk["metadata"] if isinstance(chunk["metadata"], dict) else {}
            q = await generate_question(
                chunk_id=chunk["id"],
                content=chunk["content"],
                metadata=metadata,
                client=client,
            )
            if q:
                results.append(q)
                sys.stdout.write(f"\r  Generated {len(results)} questions...")
                sys.stdout.flush()

    async with httpx.AsyncClient() as client:
        tasks = [process(c) for c in chunks]
        await asyncio.gather(*tasks)

    print(f"\nGenerated {len(results)} new questions from chunks")

    all_questions = existing + results
    before_dedup = len(all_questions)
    all_questions = deduplicate(all_questions)
    removed = before_dedup - len(all_questions)
    if removed:
        print(f"Removed {removed} duplicates")

    # Summary by domain
    domains: dict[str, int] = {}
    for q in all_questions:
        d = q.get("domain", "unknown")
        domains[d] = domains.get(d, 0) + 1
    print(f"Total: {len(all_questions)} questions")
    for domain, count in sorted(domains.items()):
        print(f"  {domain}: {count}")

    OUTPUT_FILE.write_text(json.dumps(all_questions, ensure_ascii=False, indent=2))
    print(f"Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate PMP questions from PMBOK chunks")
    parser.add_argument("--limit", type=int, default=None, help="Max chunks to process")
    parser.add_argument("--clear", action="store_true", help="Clear existing questions.json first")
    args = parser.parse_args()

    asyncio.run(main(limit=args.limit, clear=args.clear))
