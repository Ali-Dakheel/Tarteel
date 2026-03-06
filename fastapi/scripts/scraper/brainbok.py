"""
Scraper for BrainBOK's free PMP situational practice exam.
URL: https://www.brainbok.com/blog/pmp/pmp-practice-exam-free-situational-questions/

Format: HTML blog post with Q&A in structured divs/lists.
50 situational questions, high quality, 100% scenario-based.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import clean_text, detect_domain, fetch_html, normalize

SOURCE = "BrainBOK"
URL = "https://www.brainbok.com/blog/pmp/pmp-practice-exam-free-situational-questions/"


def scrape() -> list[dict]:
    print(f"  [{SOURCE}] Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"  [{SOURCE}] ERROR: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    questions: list[dict] = []

    # BrainBOK uses ordered lists (ol/li) for questions and options
    # and paragraph tags for answers/explanations
    content_area = soup.find("article") or soup.find("main") or soup.find("div", class_=re.compile(r"content|post|entry"))

    if not content_area:
        content_area = soup

    text_blocks = content_area.get_text(separator="\n")
    lines = [l.strip() for l in text_blocks.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        line = lines[i]

        # Detect question: "1.", "Q1.", "Question 1" etc.
        q_match = re.match(r'^(?:Q\.?\s*)?(\d+)[.)]\s+(.+)', line, re.IGNORECASE)
        if not q_match:
            i += 1
            continue

        stem_parts = [clean_text(q_match.group(2))]
        i += 1

        # Multi-line stem: keep accumulating until we hit option A
        while i < len(lines):
            if re.match(r'^[A-Da-d][.)]\s+', lines[i]):
                break
            if re.match(r'^(?:Q\.?\s*)?\d+[.)]\s+', lines[i], re.IGNORECASE):
                break
            stem_parts.append(clean_text(lines[i]))
            i += 1

        stem = " ".join(p for p in stem_parts if p)

        options: list[str] = []
        while i < len(lines) and len(options) < 4:
            opt_match = re.match(r'^([A-Da-d])[.)]\s+(.+)', lines[i])
            if opt_match:
                options.append(clean_text(opt_match.group(2)))
                i += 1
            else:
                break

        if len(options) != 4:
            continue

        correct_option: int | None = None
        explanation = ""

        # Find answer
        while i < len(lines):
            ans_match = re.search(r'[Aa]nswer[:\s]+([A-Da-d])', lines[i])
            if ans_match:
                letter = ans_match.group(1).upper()
                correct_option = ord(letter) - ord('A')
                rest = lines[i][ans_match.end():].strip()
                if rest:
                    explanation = clean_text(rest)
                i += 1
                while i < len(lines):
                    if re.match(r'^(?:Q\.?\s*)?\d+[.)]\s+', lines[i], re.IGNORECASE):
                        break
                    if lines[i]:
                        explanation = (explanation + " " + clean_text(lines[i])).strip()
                    i += 1
                break
            if re.match(r'^(?:Q\.?\s*)?\d+[.)]\s+', lines[i], re.IGNORECASE):
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
