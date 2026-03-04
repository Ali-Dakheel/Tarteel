"""
PDF ingestion script — Pipeline A.

Extracts text from all PDFs in fastapi/data/, splits into chunks,
embeds with bge-m3, and upserts into pmp_chunks with domain metadata.

pmp_chunks.lesson_id is nullable — PDF chunks have no parent lesson.
Domain is auto-detected: ECO files use section headers; other PDFs
use keyword scoring across the three PMP exam domains.

Usage (inside Docker):
    docker exec -it tarteel_fastapi uv run python scripts/pdf_ingest.py
    docker exec -it tarteel_fastapi uv run python scripts/pdf_ingest.py --file "New-PMP-Examination-Content-Outline-2026.pdf"
"""

import argparse
import asyncio
import json
import os
import re
import sys
from pathlib import Path

import asyncpg
import fitz  # pymupdf
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
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")
EMBEDDING_MODEL = "bge-m3"
CHUNK_SIZE_WORDS = 400
CHUNK_OVERLAP_WORDS = 50
BATCH_SIZE = 8
DATA_DIR = Path(__file__).parent.parent / "data"

# ---------------------------------------------------------------------------
# Domain detection
# ---------------------------------------------------------------------------

# ECO PDFs have explicit domain section headers — detect by scanning page text.
_ECO_HEADERS: dict[str, str] = {
    "domain i:": "people",
    "domain i ": "people",
    "domain 1:": "people",
    "domain ii:": "process",
    "domain ii ": "process",
    "domain 2:": "process",
    "domain iii:": "business-environment",
    "domain iii ": "business-environment",
    "domain 3:": "business-environment",
}

# Keyword sets for non-ECO PDFs (scored per chunk).
_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "people": [
        "leadership", "leader", "team", "stakeholder", "conflict",
        "negotiation", "negotiat", "mentor", "coach", "culture",
        "servant", "motivat", "emotional", "communication", "communicat",
        "collaborat", "empower", "diversity", "engagement", "interpersonal",
        "sponsor", "influenc", "facilitat", "trust", "ethics",
    ],
    "process": [
        "schedule", "scope", "cost", "quality", "risk", "procurement",
        "wbs", "critical path", "earned value", "baseline", "charter",
        "deliverable", "milestone", "sprint", "backlog", "velocity",
        "burndown", "kanban", "iteration", "integration", "change control",
        "monitor", "execute", "initiat", "planning", "artifact",
        "estimate", "forecast", "variance", "index", "buffer",
    ],
    "business-environment": [
        "strategy", "strategic", "governance", "compliance", "portfolio",
        "program", "organizational", "benefits", "pmo", "roi",
        "business case", "sustainability", "regulatory", "audit",
        "enterprise", "value delivery", "business value", "market",
        "economic", "competitive", "external environment",
    ],
}


def _is_eco_file(filename: str) -> bool:
    lower = filename.lower()
    return "eco" in lower or "examination-content-outline" in lower or "content-outline" in lower


def detect_domain_by_header(text: str, current: str) -> str:
    """Scan page text for ECO domain section markers; carry forward if not found."""
    lower = text.lower()
    for marker, domain in _ECO_HEADERS.items():
        if marker in lower:
            return domain
    return current


def detect_domain_by_keywords(text: str) -> str:
    """Score chunk text against keyword sets; return highest-scoring domain."""
    lower = text.lower()
    scores: dict[str, int] = {d: 0 for d in _DOMAIN_KEYWORDS}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        for kw in keywords:
            scores[domain] += lower.count(kw)
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "process"  # default to process


# ---------------------------------------------------------------------------
# Text extraction and cleaning
# ---------------------------------------------------------------------------

def clean_text(text: str) -> str:
    """Strip PMI footers, standalone page numbers, normalise whitespace."""
    text = re.sub(
        r"©\s*20\d{2}\s+Project Management Institute[^\n]*", "", text, flags=re.IGNORECASE
    )
    text = re.sub(r"(?m)^\s*\d{1,4}\s*$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r" {2,}", " ", text)
    return text.strip()


def _extract_visible_text(page: fitz.Page) -> str:
    """
    Extract only visible text from a PyMuPDF page, filtering hidden layers.

    PDFs from unofficial sources (e.g. dokumen.pub) often embed a hidden OCR
    text layer (white/near-white colored spans) behind the visible rendered text.
    pdfplumber extracts both layers merged together, producing garbled output.
    PyMuPDF lets us inspect each span's color — we skip any near-white span
    (RGB > 240,240,240) which is the classic invisible-OCR-layer signature.
    """
    parts: list[str] = []
    blocks = page.get_text("dict", flags=fitz.TEXT_DEHYPHENATE)["blocks"]
    for block in blocks:
        if block["type"] != 0:  # skip image blocks
            continue
        for line in block["lines"]:
            line_parts: list[str] = []
            for span in line["spans"]:
                color: int = span["color"]
                r = (color >> 16) & 0xFF
                g = (color >> 8) & 0xFF
                b = color & 0xFF
                # Skip near-white text (hidden OCR layer)
                if r > 240 and g > 240 and b > 240:
                    continue
                line_parts.append(span["text"])
            if line_parts:
                parts.append(" ".join(line_parts))
        parts.append("\n")
    return "\n".join(parts)


def extract_pages(pdf_path: Path) -> list[tuple[int, str]]:
    """
    Return [(page_num, cleaned_text), ...] skipping image-only and unrecoverable pages.
    Uses PyMuPDF with color filtering to exclude hidden OCR text layers.
    """
    pages: list[tuple[int, str]] = []

    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc, start=1):
            try:
                raw = _extract_visible_text(page)
                cleaned = clean_text(raw)
                if len(cleaned.split()) < 20:
                    continue  # image-only / near-empty
                pages.append((i, cleaned))
            except Exception:
                continue

    return pages


# ---------------------------------------------------------------------------
# Chunking (same logic as ingest.py)
# ---------------------------------------------------------------------------

def split_into_chunks(
    text: str,
    size: int = CHUNK_SIZE_WORDS,
    overlap: int = CHUNK_OVERLAP_WORDS,
) -> list[str]:
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
# DB upsert
# ---------------------------------------------------------------------------

# Each item: (chunk_text, domain_slug, page_num)
ChunkMeta = tuple[str, str, int]


async def upsert_pdf_chunks(
    conn: asyncpg.Connection,
    source: str,
    chunks_with_meta: list[ChunkMeta],
    embeddings: list[list[float]],
) -> int:
    # Idempotent: remove any prior chunks for this source file
    await conn.execute(
        "DELETE FROM pmp_chunks WHERE metadata->>'source' = $1", source
    )

    inserted = 0
    for idx, ((content, domain, page), embedding) in enumerate(
        zip(chunks_with_meta, embeddings)
    ):
        vector_literal = f"[{','.join(str(x) for x in embedding)}]"
        metadata = json.dumps({"domain": domain, "source": source, "page": page})
        await conn.execute(
            """
            INSERT INTO pmp_chunks (lesson_id, content, metadata, chunk_index, created_at, updated_at)
            VALUES (NULL, $1, $2::jsonb, $3, NOW(), NOW())
            """,
            content,
            metadata,
            idx,
        )
        await conn.execute(
            f"UPDATE pmp_chunks SET embedding = '{vector_literal}'::vector "
            "WHERE lesson_id IS NULL AND metadata->>'source' = $1 AND chunk_index = $2",
            source,
            idx,
        )
        inserted += 1
    return inserted


# ---------------------------------------------------------------------------
# Per-PDF orchestration
# ---------------------------------------------------------------------------

async def ingest_pdf(
    pdf_path: Path,
    conn: asyncpg.Connection,
    client: httpx.AsyncClient,
) -> int:
    source = pdf_path.name
    is_eco = _is_eco_file(source)
    print(f"\n  [{source}]")

    pages = extract_pages(pdf_path)
    if not pages:
        print("    ⚠ No extractable text — skipping (may be image-only PDF)")
        return 0

    print(f"    {len(pages)} pages with text", flush=True)

    # Build chunk list with domain labels
    chunks_with_meta: list[ChunkMeta] = []
    current_domain = "process"  # default start

    for page_num, page_text in pages:
        if is_eco:
            current_domain = detect_domain_by_header(page_text, current_domain)

        for chunk_text in split_into_chunks(page_text):
            domain = current_domain if is_eco else detect_domain_by_keywords(chunk_text)
            chunks_with_meta.append((chunk_text, domain, page_num))

    if not chunks_with_meta:
        print("    ⚠ No chunks generated — skipping")
        return 0

    print(f"    {len(chunks_with_meta)} chunks to embed", flush=True)

    # Embed in batches
    all_embeddings: list[list[float]] = []
    texts_only = [c[0] for c in chunks_with_meta]
    for i in range(0, len(texts_only), BATCH_SIZE):
        batch = texts_only[i : i + BATCH_SIZE]
        embeddings = await embed_batch(batch, client)
        all_embeddings.extend(embeddings)
        print(".", end="", flush=True)

    # Upsert
    inserted = await upsert_pdf_chunks(conn, source, chunks_with_meta, all_embeddings)

    # Domain breakdown summary
    domain_counts: dict[str, int] = {}
    for _, domain, _ in chunks_with_meta:
        domain_counts[domain] = domain_counts.get(domain, 0) + 1
    breakdown = "  ".join(f"{d}={n}" for d, n in sorted(domain_counts.items()))
    print(f"\n    ✓ {inserted} chunks  [{breakdown}]")

    return inserted


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDFs into pmp_chunks")
    parser.add_argument(
        "--file", metavar="FILENAME",
        help="Process only this filename inside fastapi/data/ (default: all PDFs)"
    )
    args = parser.parse_args()

    print(f"Connecting to DB...")
    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=3)

    async with httpx.AsyncClient() as client:
        # Ollama health check
        try:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5.0)
            r.raise_for_status()
            print(f"Ollama OK at {OLLAMA_BASE_URL}")
        except Exception as e:
            print(f"ERROR: Cannot reach Ollama at {OLLAMA_BASE_URL}: {e}")
            sys.exit(1)

        if args.file:
            pdf_files = [DATA_DIR / args.file]
        else:
            pdf_files = sorted(DATA_DIR.glob("*.pdf"))

        if not pdf_files:
            print(f"No PDFs found in {DATA_DIR}")
            sys.exit(1)

        print(f"\nFound {len(pdf_files)} PDF(s) in {DATA_DIR}")

        total_chunks = 0
        async with pool.acquire() as conn:
            for pdf_path in pdf_files:
                if not pdf_path.exists():
                    print(f"  ⚠ Not found: {pdf_path.name}")
                    continue
                total_chunks += await ingest_pdf(pdf_path, conn, client)

    await pool.close()
    print(f"\n{'=' * 60}")
    print(f"Done. Inserted {total_chunks} chunks from {len(pdf_files)} PDF(s).")


if __name__ == "__main__":
    asyncio.run(main())
