# Tarteel — Arabic-First PMP AI Tutoring Platform

## Project Overview
Bilingual Arabic/English PMP certification prep platform. Students read lessons, answer practice questions, and get RAG-powered AI explanations in Arabic. The core moat is solving code-switching — Arabic learners mixing Arabic and English technical terms in questions.

## Architecture (3 Services)
```
nextjs/          → Frontend (Next.js 15, TypeScript, Tailwind, next-intl)
laravel/         → Backend API (Laravel 12, Sanctum auth, Horizon queues)
fastapi/         → AI microservice (RAG pipeline, Ollama, pgvector)
```

## Tech Stack
- **Frontend**: Next.js 15 App Router, TypeScript strict, Tailwind v4, shadcn/ui, React Query, Zustand, next-intl
- **Backend**: Laravel 12, PHP 8.4, Sanctum, Cashier + Tap Payments, Horizon v5, Reverb v1, Filament v4
- **AI Service**: FastAPI, Ollama (Qwen3 8B), bge-m3 embeddings, bge-reranker-v2-m3, PostgreSQL + pgvector
- **Infra**: Redis (cache + queues + sessions), PostgreSQL 16, Docker Compose

## Current State (as of Phase 3 complete)
- **DB**: 1115 real PMP questions (541 People, 480 Process, 94 Business Environment), 15 lessons
- **RAG knowledge base**: 1475 chunks total — PMBOK 8th (1114), Agile Practice Guide (278), PMI ECO 2026 (43), PMI Code of Ethics (25), + 15 lesson chunks
- **Pipeline**: HyDE + multi-query expansion + multi-vector RRF merge — all live
- **Frontend**: Fully built — auth, dashboard, lesson pages, question cards, SSE AI explanation, free-form tutor chat
- **Question source**: ExamTopics PDF (1117 questions, AI-answered by Qwen3) + live ExamTopics page 1 (10 questions with confirmed answers)

## Dev Commands
```bash
# Start all services
docker-compose up -d

# FastAPI scripts (run inside container)
docker exec tarteel_fastapi uv run python scripts/pdf_ingest.py           # re-ingest PDFs
docker exec tarteel_fastapi uv run python scripts/seed_questions.py --clear  # seed questions
docker exec tarteel_fastapi uv run python scripts/scraper/run_all.py      # scrape + generate questions.json

# Rebuild chunks from scratch
docker exec tarteel_postgres psql -U tarteel -d tarteel -c "DELETE FROM pmp_chunks WHERE lesson_id IS NULL;"
docker exec tarteel_fastapi uv run python scripts/pdf_ingest.py
docker exec tarteel_redis redis-cli FLUSHDB

# Laravel
php artisan migrate
php artisan test

# Next.js
cd nextjs && npm run dev    # port 3000
npm run build
npm run lint

# Pull Ollama models (once)
docker exec -it tarteel_ollama ollama pull bge-m3
docker exec -it tarteel_ollama ollama pull qllama/bge-reranker-v2-m3
docker exec -it tarteel_ollama ollama pull qwen3:8b
```

## Key Files
```
fastapi/
  ├── app/rag/pipeline.py        ← full RAG pipeline (HyDE + expansion + RRF + rerank + generate)
  ├── app/rag/hyde.py            ← HyDE: generates hypothetical passage before vector search
  ├── app/rag/query_expansion.py ← multi-query: 2 rephrasings for extra vector recall
  ├── app/rag/embeddings.py      ← bge-m3 embedding logic
  ├── app/rag/retrieval.py       ← hybrid BM25 + pgvector + RRF fusion
  ├── app/rag/reranker.py        ← bge-reranker-v2-m3 cross-encoder
  ├── app/prompts.py             ← Arabic/English system prompts with grounding instruction
  ├── scripts/pdf_ingest.py      ← PDF → chunks with [Source | Section | Domain] prefix
  ├── scripts/seed_questions.py  ← questions.json → DB with LESSON_KEYWORDS smart assignment
  └── scripts/scraper/
      ├── run_all.py             ← orchestrator: scrape → deduplicate → save questions.json
      ├── base.py                ← normalize(), deduplicate(), detect_domain(), fetch_html()
      ├── examtopics.py          ← Playwright: live scrape page 1 (10 free questions + answers)
      └── examtopics_pdf.py      ← PDF parse (PyMuPDF) + Qwen3 answer generation (~1117 Qs)

laravel/
  ├── app/Jobs/                  ← async AI jobs dispatched to Horizon
  ├── app/Http/Resources/        ← API response transformers
  └── app/Models/                ← User, Lesson, Question, Progress, Chunk

nextjs/
  ├── app/[locale]/(dashboard)/learn/[domain]/[lesson]/page.tsx ← lesson + question + AI flow
  ├── app/[locale]/(dashboard)/tutor/page.tsx                   ← free-form AI chat
  ├── components/learn/AiExplanation.tsx  ← SSE stream consumer (card + chat variants)
  ├── components/learn/QuestionCard.tsx   ← answer → feedback → auto-stream AI explanation
  └── lib/api/                            ← typed API clients
```

## RAG Pipeline — Current Architecture (IMPORTANT)
Always follow this exact order — never skip steps:

1. **Metadata routing** — domain + lesson_id from request, no LLM call
2. **Parallel Stage** (run with `asyncio.gather`):
   - HyDE: Qwen3 generates a short hypothetical book passage → embed for primary vector search
   - Multi-query expansion: Qwen3 generates 2 rephrasings → each embedded separately
3. **Multi-vector retrieval**: BM25 (original question) + vector (hypothesis) → RRF, then merge each expansion's vector results via `_merge_rrf()`
4. **Fetch + re-sort** top chunks by merged RRF score
5. **Top 8 chunks** assembled with source/page prefix for citation
6. **Generation**: Qwen3 8B via Ollama with SSE streaming

```
retrieval_limit = 40 (no lesson) | 25 (with lesson)
top_chunks = 8 after RRF merge
```

### HyDE — Critical Lesson Learned
Qwen3 8B has a thinking mode that consumes tokens BEFORE producing output. Always set:
```python
"think": False,          # skip thinking phase
"options": {"num_predict": 150}  # enough tokens for actual output
```
Without `think: False`, Qwen3 uses all `num_predict` tokens on internal reasoning and returns empty response.

### Multi-query — Arabic code-switching
For Arabic questions, the expansion prompt instructs Qwen3 to produce one Arabic rewrite + one English translation. This is critical because the knowledge base is English-only (PMBOK, Agile Guide, etc.) — the English translation vector bridges the semantic gap.

## PDF Ingestion — Contextual Chunk Prefix
Every chunk is prefixed before embedding with:
```
[PMBOK 8th Edition | Risk Management Planning | Process Domain]
chunk text here...
```
This gives bge-m3 explicit source + section + domain context on every chunk. The three signals that matter most for PMP retrieval. Format: `[{display_source} | {current_header} | {domain_label}]`.

**NEVER ingest the ExamTopics question bank PDF** (`examtopics_pmp.pdf`) into pmp_chunks — it's questions, not knowledge. It's in `_SKIP_PDFS` in `pdf_ingest.py`.

PDF data directory: `/app/data/` inside container = `fastapi/data/` on host (gitignored).
Currently: PMBOK 8th, Agile Practice Guide, PMI ECO 2026, PMI Code of Ethics, examtopics_pmp.pdf.

## Question Bank
- **Source**: ExamTopics PDF (1117 raw Qs, no answers) + Playwright live scrape (10 Qs with confirmed answers)
- **Answer generation**: Qwen3 8B with `temperature: 0.0, num_predict: 5, think: False` — extracts single letter A-D
- **Deduplication**: `difflib.SequenceMatcher` threshold 0.85 on question stems
- **Domain detection**: keyword frequency scoring across people/process/business-environment
- **Lesson assignment**: `LESSON_KEYWORDS` map in `seed_questions.py` — scores keyword hits per lesson slug, assigns to best match, falls back to first lesson in domain
- **questions.json**: `fastapi/data/questions.json` (gitignored) — regenerate by running `run_all.py`

## Prompts — Grounding & Hallucination Guard
Both Arabic and English system prompts include explicit grounding instructions:
- English: "If the information is not found in the provided context, say explicitly: 'I don't have enough information in the available source materials on this topic.' Do not use your internal knowledge outside the provided context."
- Arabic: "إذا لم تجد المعلومات في السياق المقدم أعلاه، قل صراحةً: 'لا تتوفر لديّ معلومات كافية...'"

Language detection: >20% Arabic Unicode characters → use Arabic prompt.
Think mode: triggered by keywords like "best describes", "most appropriate", "أفضل", "الأنسب".

## Code Conventions

### TypeScript (Next.js)
- Strict mode, no `any` types ever
- Named exports only, no default exports (except pages)
- Early returns for error states — no nested if/else
- `rtl:` / `ltr:` Tailwind modifiers for Arabic/English layout
- React Query for ALL server state, Zustand for UI state only
- `dir="auto"` on AI response text — handles mixed Arabic/English correctly

### PHP (Laravel)
- PHP 8.4 features (typed properties, match, enums)
- Eloquent ORM-first — raw queries only when ORM can't handle it
- Always use `->with()` to avoid N+1
- Form Requests for all validation, API Resources for all JSON responses
- Jobs for anything touching FastAPI
- All packages installed with `--ignore-platform-req=ext-pcntl --ignore-platform-req=ext-posix` on Windows dev

### Python (FastAPI)
- Async everywhere — `async def` for all endpoints and pipeline functions
- `httpx.AsyncClient` for all HTTP calls to Ollama — never `requests` inside async code
- Pydantic v2 models for all request/response schemas
- Type hints required on all functions
- Use `asyncio.gather()` for independent parallel LLM calls (HyDE + query expansion run together)
- Always add `.strip()` on Ollama responses before using them — model sometimes pads with whitespace

## Infrastructure — Gotchas
- Postgres: port **5433** on host (5432 taken by local pgAdmin), port 5432 inside Docker network
- Redis: no password in local dev
- FastAPI: **no public port** — internal Docker network only, accessed via Laravel proxy
- Ollama: requires `OLLAMA_HOST=0.0.0.0:11434` env var for Docker container networking
- Laravel auth: `X-Internal-Key` header + `INTERNAL_API_KEY` env var for FastAPI calls
- `docker-compose up -d` starts everything; compose file is at project root as `compose.yml`

## Arabic/RTL Rules
- Arabic explanations, English questions — never mix in the wrong direction
- Technical terms shown bilingually: `إدارة المخاطر (Risk Management)`
- `dir="ltr"` on code blocks and technical terms inside Arabic text
- `dir="auto"` on streaming AI response containers — handles code-switching naturally
- `next-intl` handles locale, never hardcode Arabic strings in components
- Test RTL layout on every change — broken RTL is a blocking bug

## Database Schema (Core Tables)
```
users, domains, lessons, questions     ← content and users
user_progress, question_attempts       ← learning tracking
user_streaks, xp_events                ← gamification
pmp_chunks                             ← RAG knowledge base (pgvector, 1024-dim bge-m3)
ai_response_cache                      ← LLM response cache (Redis key: SHA256 of query+context)
```

pmp_chunks notable columns: `content` (text with prefix), `metadata` (JSON: source, page, domain), `embedding` (vector 1024), `lesson_id` (NULL for PDF chunks).

## Inter-Service Auth
- Laravel issues Sanctum Bearer tokens
- Frontend → Laravel API (Bearer token in Authorization header)
- Laravel → FastAPI (X-Internal-Key header for non-SSE calls)
- SSE streaming: Frontend → Laravel → StreamedResponse proxy → FastAPI (SSE bypass)
- FastAPI validates via `INTERNAL_API_KEY` env var

## Environment Variables
```bash
# Never commit .env files — use .env.example
APP_KEY=                    # Laravel app key
INTERNAL_API_KEY=           # FastAPI auth header value
DATABASE_URL=               # PostgreSQL connection string (asyncpg format)
REDIS_URL=                  # Redis connection
OLLAMA_BASE_URL=            # http://ollama:11434 in Docker, http://localhost:11434 locally
TAP_SECRET_KEY=             # Tap Payments (GCC payment gateway)
```

## MVP Scope (V1 Only)
**IN**: 3 PMP domains, 15 lessons, 1115 questions, RAG AI tutor, bilingual toggle, progress tracking, streak/XP, auth, freemium gate ($14.99/mo Pro via Tap Payments)
**OUT**: AWS/CFA tracks, video, leaderboards, mobile app, B2B dashboard, document upload, mock exams, flashcards

## IMPORTANT Rules
- NEVER use `any` in TypeScript
- NEVER call Ollama directly from Laravel — always go through FastAPI
- NEVER return raw Eloquent models from API endpoints — use Resources
- NEVER store sensitive data in localStorage — use httpOnly cookies via Sanctum
- NEVER ingest question-bank PDFs (examtopics_pmp.pdf) into pmp_chunks — questions ≠ knowledge
- ALWAYS cache LLM responses in Redis (key: SHA256 of query + retrieved chunks)
- ALWAYS keep retrieved context under 4K tokens for Qwen3 8B
- ALWAYS set `think: False` on Qwen3 Ollama calls that need short/fast output
- ALWAYS flush Redis after re-ingesting PDFs: `docker exec tarteel_redis redis-cli FLUSHDB`
- ALWAYS run `npm run lint` and `php artisan test` before committing