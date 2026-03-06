"""
ExamTopics PDF parser + AI answer generation.

The ExamTopics PDF has ~1350 real PMP exam questions but no answers.
This script:
1. Parses all Q+options from the PDF
2. Uses Qwen3 (with PMP expertise) to select the correct option for each question
3. Returns normalized question dicts

This is the highest-volume source of near-real exam questions.
"""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

import fitz
import httpx

from .base import clean_text, detect_domain, normalize

SOURCE = "ExamTopics"
PDF_PATH = Path("/app/data/examtopics_pmp.pdf")
OLLAMA_URL = "http://ollama:11434"
MODEL = "qwen3:8b"


def _letter_to_index(letter: str) -> int | None:
    return {"A": 0, "B": 1, "C": 2, "D": 3}.get(letter.strip().upper())


def parse_pdf_questions() -> list[dict]:
    """Extract raw question dicts (no answers) from the ExamTopics PDF."""
    if not PDF_PATH.exists():
        print(f"  [ExamTopics PDF] PDF not found at {PDF_PATH}")
        return []

    doc = fitz.open(str(PDF_PATH))
    all_text_lines: list[str] = []

    for page in doc:
        raw = page.get_text()
        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue
            # Skip page header noise (URLs, dates, page numbers)
            if "examtopics.com" in line.lower():
                continue
            if re.match(r"^\d+/\d+/\d+", line):
                continue
            if re.match(r"^\d+/\d+$", line):
                continue
            all_text_lines.append(line)

    doc.close()

    # Parse questions from cleaned text
    questions: list[dict] = []
    i = 0
    n = len(all_text_lines)

    while i < n:
        line = all_text_lines[i]

        # Detect question start: "Question #N"
        if not re.match(r"^Question\s+#\d+", line, re.IGNORECASE):
            i += 1
            continue

        i += 1
        # Skip "Topic N" lines
        while i < n and re.match(r"^Topic\s+\d+", all_text_lines[i], re.IGNORECASE):
            i += 1

        # Collect stem
        stem_parts: list[str] = []
        while i < n:
            current = all_text_lines[i]
            if re.match(r"^[A-D]\.\s+", current):
                break
            if re.match(r"^Question\s+#\d+", current, re.IGNORECASE):
                break
            stem_parts.append(clean_text(current))
            i += 1

        stem = " ".join(p for p in stem_parts if p)
        if not stem or len(stem) < 20:
            continue

        # Collect options A-D
        options: list[str] = []
        for expected_letter in ["A", "B", "C", "D"]:
            if i >= n:
                break
            opt_match = re.match(rf"^{expected_letter}\.\s+(.+)", all_text_lines[i])
            if not opt_match:
                break
            opt_text = clean_text(opt_match.group(1))
            i += 1
            # Multi-line option continuation
            while i < n:
                next_line = all_text_lines[i]
                if re.match(r"^[A-D]\.\s+", next_line):
                    break
                if re.match(r"^Question\s+#\d+", next_line, re.IGNORECASE):
                    break
                opt_text = (opt_text + " " + clean_text(next_line)).strip()
                i += 1
            options.append(opt_text)

        if len(options) == 4:
            questions.append({
                "stem": stem,
                "options": options,
                "domain": detect_domain(stem),
            })

    print(f"  [ExamTopics PDF] Parsed {len(questions)} questions from PDF")
    return questions


async def _ask_qwen3_for_answer(
    stem: str,
    options: list[str],
    client: httpx.AsyncClient,
) -> int | None:
    """Ask Qwen3 to select the correct PMP answer. Returns 0-3 or None on failure."""
    opts_text = "\n".join(f"{chr(65+i)}. {opt}" for i, opt in enumerate(options))
    prompt = (
        "You are a PMP certification expert. Select the BEST answer for this PMP exam question. "
        "Output ONLY the letter (A, B, C, or D). No explanation, no punctuation.\n\n"
        f"Question: {stem}\n\n{opts_text}"
    )
    try:
        r = await client.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {"num_predict": 5, "temperature": 0.0},
            },
            timeout=20.0,
        )
        r.raise_for_status()
        response = r.json().get("response", "").strip().upper()
        # Extract single letter
        letter_match = re.search(r"\b([A-D])\b", response)
        if letter_match:
            return _letter_to_index(letter_match.group(1))
    except Exception:
        pass
    return None


async def _generate_answers(raw_questions: list[dict], batch_size: int = 5) -> list[dict]:
    """Generate answers for all questions using Qwen3 (concurrent batches)."""
    results: list[dict] = []
    total = len(raw_questions)
    answered = 0

    async with httpx.AsyncClient() as client:
        for start in range(0, total, batch_size):
            batch = raw_questions[start : start + batch_size]
            tasks = [
                _ask_qwen3_for_answer(q["stem"], q["options"], client)
                for q in batch
            ]
            answers = await asyncio.gather(*tasks)

            for q, answer in zip(batch, answers):
                if answer is None:
                    continue
                raw = {
                    "stem": q["stem"],
                    "options": q["options"],
                    "correct_option": answer,
                    "explanation": "",
                    "difficulty": "medium",
                    "domain": q["domain"],
                }
                normalized = normalize(raw, SOURCE)
                if normalized:
                    results.append(normalized)

            answered += len(batch)
            pct = answered / total * 100
            print(f"  [ExamTopics PDF] Answered {answered}/{total} ({pct:.0f}%)  valid={len(results)}", flush=True)

    return results


def scrape(max_questions: int = 1200) -> list[dict]:
    """Parse PDF and AI-generate answers. Returns normalized question list."""
    print(f"  [ExamTopics PDF] Starting PDF parse + AI answer generation")
    raw = parse_pdf_questions()
    if not raw:
        return []

    # Limit to avoid extremely long runs
    if len(raw) > max_questions:
        print(f"  [ExamTopics PDF] Limiting to {max_questions} questions")
        raw = raw[:max_questions]

    questions = asyncio.run(_generate_answers(raw))
    print(f"  [ExamTopics PDF] Final count: {len(questions)} questions with answers")
    return questions
