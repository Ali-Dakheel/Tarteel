"""
Orchestrator: runs all scrapers, deduplicates, and saves to fastapi/data/questions.json.

Usage (inside Docker):
    uv run python scripts/scraper/run_all.py

Output:
    fastapi/data/questions.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Add project root to path so imports work
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from scripts.scraper import examtopics, examtopics_pdf
from scripts.scraper.base import deduplicate, detect_domain

OUTPUT_FILE = Path(__file__).parent.parent.parent / "data" / "questions.json"


def main() -> None:
    print("=" * 60)
    print("PMP Question Scraper — collecting from all sources")
    print("=" * 60)

    all_questions: list[dict] = []

    scrapers = [
        examtopics.scrape,        # 10 questions from page 1 (answers freely revealed)
        examtopics_pdf.scrape,    # ~1200 questions from PDF + Qwen3-generated answers
    ]

    for scraper_fn in scrapers:
        try:
            questions = scraper_fn()
            all_questions.extend(questions)
        except Exception as e:
            print(f"  ERROR in {scraper_fn.__module__}: {e}")

    print(f"\nTotal raw questions: {len(all_questions)}")

    # Deduplicate by stem similarity
    unique = deduplicate(all_questions, threshold=0.85)
    print(f"After deduplication: {len(unique)}")

    # Re-classify domain for any that defaulted wrong
    for q in unique:
        if not q.get("domain") or q["domain"] == "process":
            # Re-run domain detection with explanation included
            detected = detect_domain(q["stem"], q.get("explanation", ""))
            q["domain"] = detected

    # Domain breakdown
    domain_counts: dict[str, int] = {}
    for q in unique:
        domain_counts[q["domain"]] = domain_counts.get(q["domain"], 0) + 1
    print("\nDomain breakdown:")
    for domain, count in sorted(domain_counts.items()):
        print(f"  {domain}: {count}")

    # Source breakdown
    source_counts: dict[str, int] = {}
    for q in unique:
        source_counts[q["source"]] = source_counts.get(q["source"], 0) + 1
    print("\nSource breakdown:")
    for source, count in sorted(source_counts.items()):
        print(f"  {source}: {count}")

    # Save
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_FILE.write_text(
        json.dumps(unique, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n✓ Saved {len(unique)} questions to {OUTPUT_FILE}")
    print("=" * 60)
    print("Next: run  uv run python scripts/seed_questions.py --clear")


if __name__ == "__main__":
    main()
