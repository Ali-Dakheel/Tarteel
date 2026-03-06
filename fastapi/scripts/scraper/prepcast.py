"""
Scraper for PM PrepCast's free 120 PMP practice questions.
URL: https://www.project-management-prepcast.com/pmp-practice-exam-questions-sample-test

Format: HTML page with JS-rendered quiz OR static question blocks.
Falls back to text-based parsing if JS rendering is not available.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import clean_text, detect_domain, fetch_html, normalize

SOURCE = "PrepCast"
URL = "https://www.project-management-prepcast.com/pmp-practice-exam-questions-sample-test"

# Alternative static question pages PrepCast publishes
STATIC_URLS = [
    "https://www.project-management-prepcast.com/free-pmp-practice-exam/pmp-practice-exam-questions-and-answers",
]


def _parse_text_blocks(text: str) -> list[dict]:
    """Generic line-by-line Q&A parser."""
    questions: list[dict] = []
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    i = 0
    while i < len(lines):
        line = lines[i]
        q_match = re.match(r'^(?:Question\s+)?(\d+)[.)]\s+(.+)', line, re.IGNORECASE)
        if not q_match:
            i += 1
            continue

        stem_parts = [clean_text(q_match.group(2))]
        i += 1
        while i < len(lines) and not re.match(r'^[A-Da-d][.)]\s+', lines[i]):
            if re.match(r'^(?:Question\s+)?\d+[.)]\s+', lines[i], re.IGNORECASE):
                break
            stem_parts.append(clean_text(lines[i]))
            i += 1

        stem = " ".join(p for p in stem_parts if p)
        options: list[str] = []
        while i < len(lines) and len(options) < 4:
            opt = re.match(r'^([A-Da-d])[.)]\s+(.+)', lines[i])
            if opt:
                options.append(clean_text(opt.group(2)))
                i += 1
            else:
                break

        if len(options) != 4:
            continue

        correct_option: int | None = None
        explanation = ""
        while i < len(lines):
            ans = re.search(r'[Cc]orrect\s+[Aa]nswer[:\s]+([A-Da-d])|[Aa]nswer[:\s]+([A-Da-d])', lines[i])
            if ans:
                letter = (ans.group(1) or ans.group(2)).upper()
                correct_option = ord(letter) - ord('A')
                rest = lines[i][ans.end():].strip()
                if rest:
                    explanation = clean_text(rest)
                i += 1
                while i < len(lines):
                    if re.match(r'^(?:Question\s+)?\d+[.)]\s+', lines[i], re.IGNORECASE):
                        break
                    if lines[i]:
                        explanation = (explanation + " " + clean_text(lines[i])).strip()
                    i += 1
                break
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

    return questions


def scrape() -> list[dict]:
    print(f"  [{SOURCE}] Fetching {URL}")
    questions: list[dict] = []

    for url in [URL] + STATIC_URLS:
        try:
            html = fetch_html(url)
        except Exception as e:
            print(f"  [{SOURCE}] ERROR fetching {url}: {e}")
            continue

        soup = BeautifulSoup(html, "html.parser")

        # Try structured extraction: look for question containers
        q_containers = soup.find_all("div", class_=re.compile(r"question|quiz|exam", re.I))
        if not q_containers:
            q_containers = soup.find_all("li", class_=re.compile(r"question", re.I))

        if q_containers:
            for container in q_containers:
                text = container.get_text(separator="\n")
                parsed = _parse_text_blocks(text)
                questions.extend(parsed)
        else:
            # Full-page text fallback
            content_area = (
                soup.find("article")
                or soup.find("main")
                or soup.find("div", {"id": re.compile(r"content|main", re.I)})
                or soup
            )
            text = content_area.get_text(separator="\n")
            questions.extend(_parse_text_blocks(text))

        if questions:
            break  # Got enough from first URL

    print(f"  [{SOURCE}] Scraped {len(questions)} questions")
    return questions
