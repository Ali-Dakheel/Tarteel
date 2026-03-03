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
- **Backend**: Laravel 12, Sanctum, Cashier + Tap Payments, Horizon, Reverb, Filament v3
- **AI Service**: FastAPI, Ollama (Qwen3 8B), bge-m3 embeddings, bge-reranker-v2-m3, PostgreSQL + pgvector
- **Infra**: Redis (cache + queues + sessions), PostgreSQL 16, Docker Compose

## Dev Commands
```bash
# Start all services
docker-compose up -d

# Laravel
cd laravel && php artisan serve          # port 8000
php artisan horizon                      # queue worker
php artisan migrate
php artisan test

# FastAPI
cd fastapi && uvicorn main:app --reload  # port 8001
pytest

# Next.js
cd nextjs && npm run dev                 # port 3000
npm run build
npm run lint

# Ollama models (pull once)
ollama pull qwen3:8b
ollama pull bge-m3
ollama pull bge-reranker-v2-m3
```

## Code Conventions

### TypeScript (Next.js)
- Strict mode, no `any` types ever
- Named exports only, no default exports (except pages)
- Early returns for error states — no nested if/else
- Wisp structure: types at top, utils, component, export
- `rtl:` / `ltr:` Tailwind modifiers for Arabic/English layout
- React Query for ALL server state, Zustand for UI state only

### PHP (Laravel)
- PHP 8.3 features (typed properties, match, enums)
- Eloquent ORM-first — raw queries only when ORM can't handle it
- `select_related` equivalent: always use `->with()` to avoid N+1
- Form Requests for all validation
- API Resources for all JSON responses
- Jobs for anything touching FastAPI

### Python (FastAPI)
- Async everywhere — `async def` for all endpoints
- `httpx.AsyncClient` for all HTTP calls to Ollama
- Pydantic v2 models for all request/response schemas
- Type hints required on all functions
- Keep RAG pipeline functions pure and testable

## Key Files
```
fastapi/
  ├── rag/pipeline.py      ← full RAG pipeline (routing → retrieval → rerank → generate)
  ├── rag/embeddings.py    ← bge-m3 embedding logic
  ├── rag/retrieval.py     ← hybrid BM25 + pgvector + RRF fusion
  ├── rag/reranker.py      ← bge-reranker-v2-m3 cross-encoder
  └── prompts.py           ← system prompts (Arabic tutor persona)

laravel/
  ├── app/Jobs/            ← async AI jobs dispatched to Horizon
  ├── app/Http/Resources/  ← API response transformers
  └── app/Models/          ← User, Lesson, Question, Progress, Chunk

nextjs/
  ├── app/(dashboard)/learn/[domain]/[lesson]/  ← core learning page
  ├── app/(dashboard)/tutor/                    ← free-form AI chat
  ├── components/tutor/AiExplanation.tsx        ← SSE stream consumer
  └── lib/api/                                  ← typed API clients
```

## RAG Pipeline (IMPORTANT)
The RAG pipeline must always follow this order — never skip steps:
1. Metadata routing (domain/topic from question context) — no LLM call
2. Parallel retrieval: BM25 (PostgreSQL FTS) + dense vector (pgvector + bge-m3)
3. RRF fusion: `score = Σ 1/(60 + rank)` — top 25 candidates
4. Reranking: bge-reranker-v2-m3 cross-encoder → top 5 chunks
5. Context assembly: chunks + wrong answer + system prompt, max 4K tokens
6. Generation: Qwen3 8B via Ollama with SSE streaming

Use `/no_think` mode for factual explanations, `/think` for complex reasoning.

## Arabic/RTL Rules
- Arabic explanations, English questions — never mix in the wrong direction
- Technical terms always shown bilingually: `إدارة المخاطر (Risk Management)`
- `dir="ltr"` on all code blocks and technical terms even inside Arabic text
- `next-intl` handles locale, never hardcode Arabic strings in components
- Test RTL layout on every PR — broken RTL is a blocking bug

## Database Schema (Core Tables)
```
users, domains, lessons, questions     ← content and users
user_progress, question_attempts       ← learning tracking
user_streaks, xp_events                ← gamification
pmp_chunks                             ← RAG knowledge base (pgvector)
ai_response_cache                      ← LLM response cache (Redis key: hash of query+context)
```

## Inter-Service Auth
- Laravel issues JWT via Sanctum
- Frontend sends JWT directly to FastAPI for AI chat (SSE bypass Laravel)
- FastAPI validates JWT using shared `APP_KEY` secret
- Async AI jobs: Laravel → Redis queue → Horizon → FastAPI → PostgreSQL → Reverb WebSocket

## Environment Variables
```bash
# Never commit .env files — use .env.example
APP_KEY=                    # shared between Laravel and FastAPI for JWT validation
DATABASE_URL=               # PostgreSQL connection string
REDIS_URL=                  # Redis connection
OLLAMA_BASE_URL=            # http://ollama:11434 in Docker, http://localhost:11434 locally
TAP_SECRET_KEY=             # Tap Payments (GCC payment gateway)
```

## MVP Scope (V1 Only)
**IN**: 3 PMP domains, ~30 lessons, 150 questions, RAG AI tutor, bilingual toggle, progress tracking, streak/XP, auth, freemium gate ($14.99/mo Pro via Tap Payments)
**OUT**: AWS/CFA tracks, video, leaderboards, mobile app, B2B dashboard, document upload, mock exams, flashcards

## IMPORTANT Rules
- NEVER use `any` in TypeScript
- NEVER call Ollama directly from Laravel — always go through FastAPI
- NEVER return raw Eloquent models from API endpoints — use Resources
- NEVER store sensitive data in localStorage — use httpOnly cookies via Sanctum
- ALWAYS cache LLM responses in Redis (key: SHA256 of query + retrieved chunks)
- ALWAYS keep retrieved context under 4K tokens for Qwen3 8B
- ALWAYS run `npm run lint` and `php artisan test` before committing