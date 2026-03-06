"""
Scraper for Oliver Lehmann's free PMP practice questions.
URL: https://oliverlehmann.com/free/free-pmp-practice-questions/

Format: Static HTML page with numbered Q&A blocks.
Yields ~75 high-quality situational questions with explanations.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import clean_text, detect_domain, fetch_html, normalize

SOURCE = "Oliver Lehmann"
URL = "https://oliverlehmann.com/free/free-pmp-practice-questions/"


def scrape() -> list[dict]:
    print(f"  [{SOURCE}] Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"  [{SOURCE}] ERROR: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    questions: list[dict] = []

    # Oliver Lehmann's page uses numbered question blocks.
    # Questions are wrapped in <p> or <div> tags, answers follow below.
    # Pattern: question text, then 4 lettered options (A. B. C. D.), then answer + explanation.
    content = soup.get_text(separator="\n")
    lines = [l.strip() for l in content.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect question start: numbered line like "1.", "1)", or "Question 1"
        q_match = re.match(r'^(?:Question\s+)?(\d+)[.)]\s+(.+)', line, re.IGNORECASE)
        if not q_match:
            i += 1
            continue

        stem = clean_text(q_match.group(2))
        options: list[str] = []
        correct_option: int | None = None
        explanation = ""

        i += 1
        # Collect option lines: A. / B. / C. / D.
        while i < len(lines) and len(options) < 4:
            opt_match = re.match(r'^([A-Da-d])[.)]\s+(.+)', lines[i])
            if opt_match:
                options.append(clean_text(opt_match.group(2)))
            i += 1

        if len(options) != 4:
            continue

        # Look ahead for answer line: "Answer: C" or "Correct Answer: B"
        while i < len(lines) and i < len(lines):
            ans_match = re.search(r'[Aa]nswer[:\s]+([A-Da-d])', lines[i])
            if ans_match:
                letter = ans_match.group(1).upper()
                correct_option = ord(letter) - ord('A')
                # Collect explanation text on same or next lines
                rest = lines[i][ans_match.end():].strip()
                if rest:
                    explanation = clean_text(rest)
                i += 1
                # Grab additional explanation lines until next question
                while i < len(lines):
                    next_line = lines[i]
                    if re.match(r'^(?:Question\s+)?\d+[.)]\s+', next_line, re.IGNORECASE):
                        break
                    if re.match(r'^[A-Da-d][.)]\s+', next_line):
                        break
                    if next_line:
                        explanation = (explanation + " " + clean_text(next_line)).strip()
                    i += 1
                break
            # Stop if we hit the next question
            if re.match(r'^(?:Question\s+)?\d+[.)]\s+', lines[i], re.IGNORECASE):
                break
            i += 1

        if correct_option is None:
            continue

        raw = {
            "stem": stem,
            "options": options,
            "correct_option": correct_option,
            "explanation": explanation,
            "difficulty": "medium",
            "domain": detect_domain(stem, explanation),
        }
        normalized = normalize(raw, SOURCE)
        if normalized:
            questions.append(normalized)

    print(f"  [{SOURCE}] Scraped {len(questions)} questions")
    return questions
