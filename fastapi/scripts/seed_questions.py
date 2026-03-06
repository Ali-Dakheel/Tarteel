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

# Keywords that match each lesson slug — used to assign questions to the right lesson.
# Matched against the question stem (lowercase). Highest keyword-hit count wins.
LESSON_KEYWORDS: dict[str, list[str]] = {
    # people domain
    "leadership-styles": [
        "leadership", "management style", "servant leader", "transformational",
        "transactional", "laissez-faire", "situational leadership", "autocratic",
        "democratic", "visionary", "pacesetting", "coaching style",
    ],
    "team-building": [
        "team", "collocated", "virtual team", "remote", "distributed",
        "tuckman", "forming", "storming", "norming", "performing", "adjourning",
        "team development", "build team", "morale", "cohesion",
    ],
    "conflict-resolution": [
        "conflict", "negotiate", "negotiation", "dispute", "confrontation",
        "collaborate", "compromise", "smooth", "force", "withdraw", "avoid",
        "conflict management", "disagreement",
    ],
    "stakeholder-engagement": [
        "stakeholder", "engagement", "communication plan", "register",
        "salience", "power grid", "interest", "influence", "expectation",
        "stakeholder management", "keep informed", "manage closely",
    ],
    "coaching-mentoring": [
        "coaching", "mentoring", "develop", "career", "growth", "training",
        "performance review", "skill gap", "feedback", "improvement plan",
    ],
    # process domain
    "project-initiation": [
        "charter", "initiation", "sponsor", "business case", "feasibility",
        "project charter", "kick-off", "kickoff", "pre-project",
        "project selection", "authorize", "initiating process",
    ],
    "scope-management": [
        "scope", "wbs", "work breakdown", "requirements", "backlog",
        "product scope", "project scope", "scope creep", "gold plating",
        "scope baseline", "requirements traceability", "user story",
    ],
    "schedule-management": [
        "schedule", "critical path", "gantt", "duration", "milestone",
        "float", "slack", "lag", "lead", "network diagram", "pert",
        "fast track", "crash", "schedule baseline", "sequence activities",
    ],
    "risk-management": [
        "risk", "contingency", "probability", "impact", "monte carlo",
        "risk register", "risk response", "mitigate", "avoid", "transfer",
        "accept", "escalate", "risk appetite", "risk tolerance", "issue",
        "opportunity", "threat", "risk owner",
    ],
    "quality-change": [
        "quality", "change control", "audit", "defect", "ccb",
        "quality assurance", "quality control", "inspection", "testing",
        "integrated change control", "change request", "variance",
        "control chart", "pareto", "fishbone", "kaizen", "six sigma",
    ],
    # business-environment domain
    "org-strategy": [
        "strategy", "strategic", "portfolio", "program", "vision",
        "mission", "organizational strategy", "enterprise", "strategic alignment",
        "strategic objective", "competitive advantage",
    ],
    "benefits-realization": [
        "benefit", "roi", "return on investment", "value", "realization",
        "business value", "benefit owner", "transition", "sustain",
        "benefits management plan", "benefits register",
    ],
    "governance": [
        "governance", "pmo", "policy", "compliance", "oversight",
        "project management office", "audit committee", "board",
        "accountability", "responsibility", "authority", "control framework",
    ],
    "project-selection": [
        "selection", "npv", "net present value", "irr", "payback",
        "scoring model", "project prioritization", "opportunity cost",
        "cost-benefit", "weighted scoring", "benefit-cost ratio",
    ],
    "agile-hybrid": [
        "agile", "scrum", "kanban", "sprint", "hybrid", "adaptive",
        "velocity", "burndown", "retrospective", "daily standup",
        "product owner", "scrum master", "iteration", "increment",
        "definition of done", "epic", "story point", "lean",
    ],
}


# ---------------------------------------------------------------------------
# Domain + lesson lookup
# ---------------------------------------------------------------------------

async def fetch_lesson_map(conn: asyncpg.Connection) -> dict[str, dict[str, int]]:
    """
    Return nested map: {domain_slug: {lesson_slug: lesson_id}}.
    Also returns the first lesson_id per domain as a fallback.
    """
    rows = await conn.fetch(
        """
        SELECT d.slug AS domain, l.slug AS lesson_slug, l.id AS lesson_id
        FROM lessons l
        JOIN domains d ON d.id = l.domain_id
        ORDER BY d.slug, l.order
        """
    )
    result: dict[str, dict[str, int]] = {}
    for row in rows:
        domain = row["domain"]
        if domain not in result:
            result[domain] = {}
        result[domain][row["lesson_slug"]] = row["lesson_id"]
    return result


def pick_lesson(stem: str, domain: str, lesson_map: dict[str, dict[str, int]]) -> int | None:
    """
    Choose the best lesson for a question by counting LESSON_KEYWORDS matches.
    Falls back to the first lesson in the domain if no keywords match.
    """
    domain_lessons = lesson_map.get(domain, {})
    if not domain_lessons:
        return None

    stem_lower = stem.lower()
    best_lesson: str | None = None
    best_score = 0

    for lesson_slug, lesson_id in domain_lessons.items():
        keywords = LESSON_KEYWORDS.get(lesson_slug, [])
        score = sum(1 for kw in keywords if kw in stem_lower)
        if score > best_score:
            best_score = score
            best_lesson = lesson_slug

    if best_lesson:
        return domain_lessons[best_lesson]

    # Fallback: first lesson in domain (lowest id)
    return min(domain_lessons.values())


# ---------------------------------------------------------------------------
# Upsert
# ---------------------------------------------------------------------------

async def upsert_questions(
    conn: asyncpg.Connection,
    questions: list[dict],
    lesson_map: dict[str, dict[str, int]],
    clear_first: bool,
) -> tuple[int, int]:
    """Upsert questions. Returns (inserted, skipped) counts."""
    if clear_first:
        await conn.execute("DELETE FROM questions")
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
            skipped += 1
            continue
        if len(options) != 4:
            skipped += 1
            continue
        if correct_option not in (0, 1, 2, 3):
            skipped += 1
            continue
        if difficulty not in VALID_DIFFICULTIES:
            difficulty = "medium"
        if domain not in VALID_DOMAINS:
            domain = "process"

        lesson_id = pick_lesson(stem, domain, lesson_map)
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
        lesson_map = await fetch_lesson_map(conn)
        if not lesson_map:
            print("ERROR: No domains/lessons found in DB. Run migrations and seeder first.")
            sys.exit(1)

        domain_counts = {d: len(lessons) for d, lessons in lesson_map.items()}
        print(f"Lesson map: {domain_counts} lessons per domain")

        inserted, skipped = await upsert_questions(
            conn, questions, lesson_map, clear_first=args.clear
        )

    await pool.close()
    print(f"\nDone. Inserted {inserted} questions, skipped {skipped}.")


if __name__ == "__main__":
    asyncio.run(main())
