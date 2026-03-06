"""
Scraper for ExamCert's free PMP practice questions.
URL: https://www.examcert.app/exams/pmp/free-practice-test/

ExamCert is a JS SPA. Strategy:
1. Try to intercept the questions API endpoint (XHR) using Playwright network interception.
2. If API returns JSON, parse it directly — far more reliable than DOM scraping.
3. Fallback: DOM scraping of rendered HTML.

Yields 200+ questions (out of their 600+ pool, limited to what the free tier exposes).
"""

from __future__ import annotations

import json
import re
import time

from .base import clean_text, detect_domain, normalize

SOURCE = "ExamCert"
BASE_URL = "https://www.examcert.app"
EXAM_URL = f"{BASE_URL}/exams/pmp/free-practice-test/"


def _letter_to_index(letter: str) -> int | None:
    letter = letter.strip().upper()
    mapping = {"A": 0, "B": 1, "C": 2, "D": 3}
    return mapping.get(letter)


def _parse_api_response(data: dict | list) -> list[dict]:
    """Parse ExamCert API JSON response into canonical question format."""
    questions: list[dict] = []

    # Handle different API response shapes
    items = data if isinstance(data, list) else data.get("questions", data.get("data", []))

    for item in items:
        if not isinstance(item, dict):
            continue

        stem = clean_text(str(item.get("question", item.get("stem", item.get("text", "")))))
        if not stem:
            continue

        # Options may be a list of strings or list of {text, label} dicts
        raw_options = item.get("options", item.get("answers", item.get("choices", [])))
        options: list[str] = []
        for opt in raw_options:
            if isinstance(opt, str):
                options.append(clean_text(opt))
            elif isinstance(opt, dict):
                text = opt.get("text", opt.get("answer", opt.get("content", "")))
                options.append(clean_text(str(text)))

        if len(options) != 4:
            continue

        # Correct answer: may be index, letter, or answer text
        correct_raw = item.get("correct_answer", item.get("answer", item.get("correct", item.get("correct_option"))))
        correct_option: int | None = None

        if isinstance(correct_raw, int) and 0 <= correct_raw <= 3:
            correct_option = correct_raw
        elif isinstance(correct_raw, str):
            if correct_raw.upper() in ("A", "B", "C", "D"):
                correct_option = _letter_to_index(correct_raw)
            else:
                # May be the answer text — find matching option
                for idx, opt in enumerate(options):
                    if clean_text(correct_raw).lower() == opt.lower():
                        correct_option = idx
                        break

        if correct_option is None:
            continue

        explanation = clean_text(str(item.get("explanation", item.get("rationale", item.get("reason", "")))))
        difficulty_raw = str(item.get("difficulty", item.get("level", "medium"))).lower()
        difficulty = difficulty_raw if difficulty_raw in ("easy", "medium", "hard") else "medium"

        raw = {
            "stem": stem,
            "options": options,
            "correct_option": correct_option,
            "explanation": explanation,
            "difficulty": difficulty,
            "domain": detect_domain(stem, explanation),
        }
        normalized = normalize(raw, SOURCE)
        if normalized:
            questions.append(normalized)

    return questions


def _scrape_with_playwright() -> list[dict]:
    """Use Playwright to intercept API calls and extract question data."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"  [{SOURCE}] Playwright not installed — skipping")
        return []

    questions: list[dict] = []
    intercepted: list[dict | list] = []

    def handle_response(response):
        url = response.url
        # Intercept JSON responses that look like question data
        if any(kw in url for kw in ["question", "exam", "quiz", "practice", "test"]):
            try:
                ct = response.headers.get("content-type", "")
                if "json" in ct:
                    data = response.json()
                    intercepted.append(data)
            except Exception:
                pass

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", handle_response)

        try:
            print(f"  [{SOURCE}] Loading {EXAM_URL} with Playwright...")
            page.goto(EXAM_URL, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(3000)

            # Scroll to trigger lazy loading
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            # Try API-intercepted data first
            for data in intercepted:
                parsed = _parse_api_response(data)
                questions.extend(parsed)

            if not questions:
                # DOM fallback: extract question text from rendered page
                html = page.content()
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(html, "html.parser")
                text = soup.get_text(separator="\n")
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                questions.extend(_parse_text_lines(lines))

        except Exception as e:
            print(f"  [{SOURCE}] Playwright error: {e}")
        finally:
            browser.close()

    return questions


def _parse_text_lines(lines: list[str]) -> list[dict]:
    """Fallback text-based parser for ExamCert DOM content."""
    questions: list[dict] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        q_match = re.match(r'^(?:Question\s+)?(\d+)[.)]\s*(.+)', line, re.IGNORECASE)
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
            ans = re.search(r'[Aa]nswer[:\s]+([A-Da-d])', lines[i])
            if ans:
                correct_option = ord(ans.group(1).upper()) - ord('A')
                rest = lines[i][ans.end():].strip()
                if rest:
                    explanation = clean_text(rest)
                i += 1
                while i < len(lines) and not re.match(r'^(?:Question\s+)?\d+[.)]\s+', lines[i], re.IGNORECASE):
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
    print(f"  [{SOURCE}] Starting (Playwright + API interception)")
    questions = _scrape_with_playwright()
    print(f"  [{SOURCE}] Scraped {len(questions)} questions")
    return questions
