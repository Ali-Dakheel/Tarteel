"""
Shared utilities for all PMP question scrapers.

Canonical question schema:
{
    "stem": str,
    "options": [str, str, str, str],   # exactly 4
    "correct_option": int,              # 0-3
    "explanation": str,
    "difficulty": "easy" | "medium" | "hard",
    "domain": "people" | "process" | "business-environment",
    "source": str,
}
"""

from __future__ import annotations

import re
import time
from difflib import SequenceMatcher
from typing import Any

import requests

# ---------------------------------------------------------------------------
# Domain detection
# ---------------------------------------------------------------------------

_DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "people": [
        "leadership", "servant leader", "team", "motivation", "conflict",
        "stakeholder", "coaching", "mentoring", "emotional intelligence",
        "negotiate", "negotiation", "collocated", "virtual team", "diversity",
        "psychological safety", "tuckman", "forming", "storming", "norming",
        "performing", "communication", "interpersonal", "empower", "delegate",
        "morale", "culture", "inclusion", "trust", "accountability",
    ],
    "business-environment": [
        "strategy", "strategic", "governance", "portfolio", "program",
        "business case", "roi", "npv", "irr", "payback", "benefit",
        "compliance", "regulation", "regulatory", "pmo", "policy",
        "organizational change", "market", "competitive", "vision",
        "mission", "stakeholder environment", "enterprise", "value",
    ],
    "process": [
        "scope", "schedule", "budget", "cost", "risk", "quality", "charter",
        "wbs", "work breakdown", "critical path", "gantt", "milestone",
        "earned value", "evm", "spi", "cpi", "change control", "ccb",
        "procurement", "contract", "vendor", "resource", "agile", "scrum",
        "sprint", "kanban", "backlog", "iteration", "waterfall", "hybrid",
        "initiation", "planning", "executing", "monitoring", "closing",
        "issue", "assumption", "constraint", "deliverable", "baseline",
    ],
}


def detect_domain(stem: str, explanation: str = "") -> str:
    """Classify question into a PMP domain by keyword frequency."""
    text = (stem + " " + explanation).lower()
    scores: dict[str, int] = {}
    for domain, keywords in _DOMAIN_KEYWORDS.items():
        scores[domain] = sum(1 for kw in keywords if kw in text)
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "process"


# ---------------------------------------------------------------------------
# Canonical normalization
# ---------------------------------------------------------------------------

_VALID_DIFFICULTIES = {"easy", "medium", "hard"}
_VALID_DOMAINS = {"people", "process", "business-environment"}


def normalize(q: dict[str, Any], source: str) -> dict[str, Any] | None:
    """
    Validate and normalize a raw question dict to the canonical schema.
    Returns None if the question is invalid.
    """
    stem = str(q.get("stem", "")).strip()
    if not stem or len(stem) < 20:
        return None

    options = q.get("options", [])
    if not isinstance(options, list) or len(options) != 4:
        return None
    options = [str(o).strip() for o in options]
    if any(len(o) < 2 for o in options):
        return None

    correct = q.get("correct_option")
    if correct not in (0, 1, 2, 3):
        return None

    explanation = str(q.get("explanation", "")).strip()
    difficulty = str(q.get("difficulty", "medium")).lower()
    if difficulty not in _VALID_DIFFICULTIES:
        difficulty = "medium"

    domain = str(q.get("domain", "")).lower().strip()
    if domain not in _VALID_DOMAINS:
        domain = detect_domain(stem, explanation)

    return {
        "stem": stem,
        "options": options,
        "correct_option": int(correct),
        "explanation": explanation or "See official PMP reference materials.",
        "difficulty": difficulty,
        "domain": domain,
        "source": source,
    }


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def _similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def deduplicate(questions: list[dict[str, Any]], threshold: float = 0.85) -> list[dict[str, Any]]:
    """Remove questions whose stem is >threshold similar to an earlier one."""
    kept: list[dict[str, Any]] = []
    stems: list[str] = []
    for q in questions:
        stem = q["stem"]
        if any(_similarity(stem, s) >= threshold for s in stems):
            continue
        kept.append(q)
        stems.append(stem)
    return kept


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_html(url: str, delay: float = 1.5) -> str:
    """Fetch URL with polite delay and browser-like headers."""
    time.sleep(delay)
    resp = requests.get(url, headers=_HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.text


def clean_text(text: str) -> str:
    """Strip excess whitespace and ExamTopics vote annotations from scraped text."""
    text = re.sub(r'\s+', ' ', text)
    # Remove "Most Voted" / "Highly Voted" suffixes added by ExamTopics community
    text = re.sub(r'\s*(Most\s+Voted|Highly\s+Voted)\s*$', '', text, flags=re.IGNORECASE)
    return text.strip()
