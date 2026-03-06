"""
Scraper for PM Study Circle's free PMP practice questions.
URLs:
  - https://pmstudycircle.com/pmp-example-questions/   (120 questions)
  - https://pmstudycircle.com/pmp-questions/           (sample set)

Format: Static HTML, structured Q&A with answer/explanation sections.
PMBOK Guide 7th Edition aligned, high quality with PMBOK references.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import clean_text, detect_domain, fetch_html, normalize

SOURCE = "PM Study Circle"

URLS = [
    "https://pmstudycircle.com/pmp-example-questions/",
    "https://pmstudycircle.com/pmp-questions/",
]


def _parse_soup(soup: BeautifulSoup) -> list[dict]:
    questions: list[dict] = []

    # PM Study Circle often wraps questions in <div class="question"> or uses
    # numbered headings followed by option lists
    content = soup.find("div", class_=re.compile(r"entry|content|post|article", re.I))
    if not content:
        content = soup

    text = content.get_text(separator="\n")
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Match "Question 1:", "1.", "Q1.", etc.
        q_match = re.match(r'^(?:Question\s+)?(\d+)[.):]\s*(.+)', line, re.IGNORECASE)
        if not q_match:
            i += 1
            continue

        stem_parts = [clean_text(q_match.group(2))]
        i += 1

        # Accumulate multi-line stem
        while i < len(lines):
            next_line = lines[i]
            if re.match(r'^[A-Da-d][.)]\s+', next_line):
                break
            if re.match(r'^(?:Question\s+)?\d+[.):]\s+', next_line, re.IGNORECASE):
                break
            if re.search(r'[Aa]nswer', next_line):
                break
            stem_parts.append(clean_text(next_line))
            i += 1

        stem = " ".join(p for p in stem_parts if p)

        options: list[str] = []
        while i < len(lines) and len(options) < 4:
            opt = re.match(r'^([A-Da-d])[.)]\s+(.+)', lines[i])
            if opt:
                options.append(clean_text(opt.group(2)))
                i += 1
            else:
                # Stop if we hit something that looks like a new question or answer marker
                if re.match(r'^(?:Question\s+)?\d+[.):]\s+', lines[i], re.IGNORECASE):
                    break
                if re.search(r'[Aa]nswer', lines[i]):
                    break
                i += 1

        if len(options) != 4:
            continue

        correct_option: int | None = None
        explanation = ""

        # Look for answer
        while i < len(lines):
            ans = re.search(
                r'[Cc]orrect\s+[Aa]nswer[:\s]+([A-Da-d])'
                r'|[Aa]nswer[:\s]+([A-Da-d])'
                r'|\(([A-Da-d])\)\s+is\s+correct',
                lines[i],
            )
            if ans:
                letter = next(g for g in ans.groups() if g).upper()
                correct_option = ord(letter) - ord('A')
                rest = lines[i][ans.end():].strip()
                if rest:
                    explanation = clean_text(rest)
                i += 1
                # Grab explanation paragraphs
                while i < len(lines):
                    if re.match(r'^(?:Question\s+)?\d+[.):]\s+', lines[i], re.IGNORECASE):
                        break
                    if lines[i]:
                        explanation = (explanation + " " + clean_text(lines[i])).strip()
                    i += 1
                break
            if re.match(r'^(?:Question\s+)?\d+[.):]\s+', lines[i], re.IGNORECASE):
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

    return questions


def scrape() -> list[dict]:
    all_questions: list[dict] = []

    for url in URLS:
        print(f"  [{SOURCE}] Fetching {url}")
        try:
            html = fetch_html(url, delay=2.0)
            soup = BeautifulSoup(html, "html.parser")
            parsed = _parse_soup(soup)
            all_questions.extend(parsed)
            print(f"  [{SOURCE}] Got {len(parsed)} from {url}")
        except Exception as e:
            print(f"  [{SOURCE}] ERROR: {e}")

    print(f"  [{SOURCE}] Total scraped: {len(all_questions)} questions")
    return all_questions
