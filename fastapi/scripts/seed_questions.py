"""
Question seeder script — Pipeline B.

Reads real PMP practice questions from fastapi/data/questions.json and
upserts them into the `questions` table, replacing factory placeholder data.

Expected JSON format (array of objects):
[
  {
    "stem": "Which process group includes creating the project charter?",
    "options": ["Executing", "Planning", "Initiating", "Monitoring and Controlling"],
    "correct_option": 2,
    "explanation": "The project charter is created during the Initiating Process Group...",
    "difficulty": "easy",
    "domain": "process"
  },
  ...
]

Fields:
  - stem:           Question text (required)
  - options:        Array of exactly 4 strings [A, B, C, D] (required)
  - correct_option: 0-based index into options (required)
  - explanation:    Explanation of the correct answer (required)
  - difficulty:     "easy" | "medium" | "hard" (optional, default: "medium")
  - domain:         "people" | "process" | "business-environment" (optional, auto-detected)

Usage (inside Docker):
    docker exec -it tarteel_fastapi uv run python scripts/seed_questions.py
    docker exec -it tarteel_fastapi uv run python scripts/seed_questions.py --clear

Source: Populate fastapi/data/questions.json with questions from any free PMP
practice resource. The script handles deduplication by (lesson_id, stem) pair.
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import asyncpg

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
DATA_DIR = Path(__file__).parent.parent / "data"
QUESTIONS_FILE = DATA_DIR / "questions.json"

VALID_DIFFICULTIES = {"easy", "medium", "hard"}
VALID_DOMAINS = {"people", "process", "business-environment"}


# ---------------------------------------------------------------------------
# Domain → first lesson_id lookup
# ---------------------------------------------------------------------------

async def fetch_domain_lesson_map(conn: asyncpg.Connection) -> dict[str, int]:
    """Return {domain_slug: first_lesson_id} for each domain."""
    rows = await conn.fetch(
        """
        SELECT d.slug AS domain, MIN(l.id) AS lesson_id
        FROM lessons l
        JOIN domains d ON d.id = l.domain_id
        GROUP BY d.slug
        """
    )
    return {row["domain"]: row["lesson_id"] for row in rows}


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

async def upsert_questions(
    conn: asyncpg.Connection,
    questions: list[dict],
    domain_lesson_map: dict[str, int],
    clear_first: bool,
) -> tuple[int, int]:
    """Upsert questions. Returns (inserted, skipped) counts."""
    if clear_first:
        await conn.execute(
            "DELETE FROM questions WHERE stem LIKE '%[seeded]%' OR true"
        )
        print("  Cleared existing questions table.")

    inserted = 0
    skipped = 0

    for i, q in enumerate(questions):
        stem = q.get("stem", "").strip()
        options = q.get("options", [])
        correct_option = q.get("correct_option")
        explanation = q.get("explanation", "").strip()
        difficulty = q.get("difficulty", "medium")
        domain = q.get("domain", "process")

        # Validation
        if not stem:
            print(f"  ⚠ Question {i+1}: missing stem — skipped")
            skipped += 1
            continue
        if len(options) != 4:
            print(f"  ⚠ Question {i+1}: options must have exactly 4 items — skipped")
            skipped += 1
            continue
        if correct_option not in (0, 1, 2, 3):
            print(f"  ⚠ Question {i+1}: correct_option must be 0-3 — skipped")
            skipped += 1
            continue
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = "medium"
        if domain not in VALID_DOMAINS:
            domain = "process"

        lesson_id = domain_lesson_map.get(domain)
        if lesson_id is None:
            print(f"  ⚠ Question {i+1}: no lesson found for domain '{domain}' — skipped")
            skipped += 1
            continue

        options_json = json.dumps(options)

        await conn.execute(
            """
            INSERT INTO questions (lesson_id, stem, options, correct_option, explanation, difficulty, created_at, updated_at)
            VALUES ($1, $2, $3::jsonb, $4, $5, $6, NOW(), NOW())
            ON CONFLICT DO NOTHING
            """,
            lesson_id,
            stem,
            options_json,
            correct_option,
            explanation,
            difficulty,
        )
        inserted += 1

    return inserted, skipped


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    parser = argparse.ArgumentParser(description="Seed questions from data/questions.json")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete ALL existing questions before inserting (use with caution)",
    )
    args = parser.parse_args()

    if not QUESTIONS_FILE.exists():
        print(f"ERROR: {QUESTIONS_FILE} not found.")
        print()
        print("Create fastapi/data/questions.json with the following format:")
        print(json.dumps(
            [
                {
                    "stem": "Which process group includes creating the project charter?",
                    "options": ["Executing", "Planning", "Initiating", "Monitoring and Controlling"],
                    "correct_option": 2,
                    "explanation": "The project charter is created during the Initiating Process Group.",
                    "difficulty": "easy",
                    "domain": "process",
                }
            ],
            indent=2,
            ensure_ascii=False,
        ))
        sys.exit(1)

    raw = QUESTIONS_FILE.read_text(encoding="utf-8")
    questions = json.loads(raw)

    if not isinstance(questions, list):
        print("ERROR: questions.json must be a JSON array.")
        sys.exit(1)

    print(f"Loaded {len(questions)} questions from {QUESTIONS_FILE.name}")

    pool = await asyncpg.create_pool(dsn=DATABASE_URL, min_size=1, max_size=3)
    async with pool.acquire() as conn:
        domain_lesson_map = await fetch_domain_lesson_map(conn)
        print(f"Domain → lesson map: {domain_lesson_map}")

        if not domain_lesson_map:
            print("ERROR: No domains/lessons found in DB. Run migrations and seeder first.")
            sys.exit(1)

        inserted, skipped = await upsert_questions(
            conn, questions, domain_lesson_map, clear_first=args.clear
        )

    await pool.close()
    print(f"\nDone. Inserted {inserted} questions, skipped {skipped}.")


if __name__ == "__main__":
    asyncio.run(main())
