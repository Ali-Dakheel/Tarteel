"""
Scraper for ExamTopics PMP free questions.
URL pattern: https://www.examtopics.com/exams/pmi/pmp/view/{page}/

ExamTopics shows 10 questions per page. Correct answers are revealed
by clicking "Reveal Solution" buttons — no login required for the answer,
only community discussions need a paid account.

1417 total questions across ~142 pages.
"""

from __future__ import annotations

import re
import time

from .base import clean_text, detect_domain, normalize

SOURCE = "ExamTopics"
BASE_URL = "https://www.examtopics.com/exams/pmi/pmp/view/{}/"

# Scrape up to this many pages (10 questions per page)
MAX_PAGES = 142


def _letter_to_index(letter: str) -> int | None:
    return {"A": 0, "B": 1, "C": 2, "D": 3}.get(letter.strip().upper())


def scrape(max_pages: int = MAX_PAGES) -> list[dict]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"  [{SOURCE}] Playwright not installed — skipping")
        return []

    all_questions: list[dict] = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        for page_num in range(1, max_pages + 1):
            url = BASE_URL.format(page_num)
            try:
                page.goto(url, wait_until="networkidle", timeout=20000)
                page.wait_for_timeout(1000)
            except Exception as e:
                print(f"  [{SOURCE}] Page {page_num}: load error — {e}")
                break

            # Click ALL "Reveal Solution" buttons on this page
            reveal_buttons = page.locator("text=Reveal Solution").all()
            if not reveal_buttons:
                print(f"  [{SOURCE}] Page {page_num}: no reveal buttons — stopping")
                break

            for btn in reveal_buttons:
                try:
                    btn.click()
                    page.wait_for_timeout(200)
                except Exception:
                    pass

            page.wait_for_timeout(500)

            # Extract page text
            text = page.inner_text("body")
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            # Parse questions from this page
            page_questions = _parse_lines(lines)
            all_questions.extend(page_questions)

            count = len(page_questions)
            print(f"  [{SOURCE}] Page {page_num}/{max_pages}: {count} questions (total: {len(all_questions)})", flush=True)

            if count == 0:
                print(f"  [{SOURCE}] No questions parsed on page {page_num} — stopping")
                break

            # Polite delay between pages
            time.sleep(1.5)

        browser.close()

    print(f"  [{SOURCE}] Total scraped: {len(all_questions)}")
    return all_questions


def _parse_lines(lines: list[str]) -> list[dict]:
    """Parse questions from ExamTopics page text lines."""
    questions: list[dict] = []
    i = 0
    n = len(lines)

    while i < n:
        # Look for "Question #N" marker
        if not re.match(r"^Question\s+#\d+$", lines[i], re.IGNORECASE):
            i += 1
            continue

        i += 1  # move past "Question #N"
        if i >= n:
            break

        # Skip "Topic N" line if present
        if re.match(r"^Topic\s+\d+", lines[i], re.IGNORECASE):
            i += 1

        # Collect stem lines until we hit option A
        stem_parts: list[str] = []
        while i < n and not re.match(r"^A\.\s+", lines[i]):
            if re.match(r"^Question\s+#\d+$", lines[i], re.IGNORECASE):
                break
            if re.match(r"^(Hide|Reveal)\s+Solution", lines[i], re.IGNORECASE):
                break
            stem_parts.append(clean_text(lines[i]))
            i += 1

        stem = " ".join(p for p in stem_parts if p)
        if not stem or len(stem) < 20:
            continue

        # Collect 4 options (A, B, C, D)
        options: list[str] = []
        option_letters = ["A", "B", "C", "D"]
        for expected in option_letters:
            if i >= n:
                break
            opt_match = re.match(rf"^{expected}\.\s+(.+)", lines[i])
            if opt_match:
                opt_text = clean_text(opt_match.group(1))
                # Option may continue on next line
                i += 1
                while i < n:
                    next_line = lines[i]
                    if re.match(r"^[A-D]\.\s+", next_line):
                        break
                    if re.match(r"^(Hide|Reveal)\s+Solution", next_line, re.IGNORECASE):
                        break
                    if re.match(r"^Question\s+#\d+$", next_line, re.IGNORECASE):
                        break
                    opt_text = (opt_text + " " + clean_text(next_line)).strip()
                    i += 1
                options.append(opt_text)
            else:
                break

        if len(options) != 4:
            continue

        # Look for "Correct Answer: X" (visible after clicking Reveal)
        correct_option: int | None = None
        while i < n:
            ca_match = re.search(r"Correct\s+Answer:\s*([A-D])", lines[i], re.IGNORECASE)
            if ca_match:
                correct_option = _letter_to_index(ca_match.group(1))
                i += 1
                break
            if re.match(r"^Question\s+#\d+$", lines[i], re.IGNORECASE):
                break
            # Skip Hide/Reveal Solution line and discussion count
            i += 1

        if correct_option is None:
            continue

        raw = {
            "stem": stem,
            "options": options,
            "correct_option": correct_option,
            "explanation": "",  # ExamTopics explanations are in community discussion (paid)
            "difficulty": "medium",
            "domain": detect_domain(stem),
        }
        normalized = normalize(raw, SOURCE)
        if normalized:
            questions.append(normalized)

    return questions
