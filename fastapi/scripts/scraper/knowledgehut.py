"""
Scraper for KnowledgeHut's free PMP exam questions blog post.
URL: https://www.knowledgehut.com/blog/project-management/pmp-exam-questions-and-answers

Format: HTML blog post with structured Q&A sections.
~60 questions with explanations per answer.
"""

from __future__ import annotations

import re

from bs4 import BeautifulSoup, Tag

from .base import clean_text, detect_domain, fetch_html, normalize

SOURCE = "KnowledgeHut"
URL = "https://www.knowledgehut.com/blog/project-management/pmp-exam-questions-and-answers"


def scrape() -> list[dict]:
    print(f"  [{SOURCE}] Fetching {URL}")
    try:
        html = fetch_html(URL)
    except Exception as e:
        print(f"  [{SOURCE}] ERROR: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    questions: list[dict] = []

    # KnowledgeHut wraps questions in h3/h4 tags with options in lists
    # Try structured extraction first
    headings = soup.find_all(["h3", "h4"], string=re.compile(r'^\s*\d+[.)]\s+', re.IGNORECASE))

    if headings:
        for heading in headings:
            stem_match = re.match(r'^\s*\d+[.)]\s+(.+)', heading.get_text(strip=True), re.IGNORECASE)
            if not stem_match:
                continue
            stem = clean_text(stem_match.group(1))

            # Gather sibling elements until next heading
            options: list[str] = []
            correct_option: int | None = None
            explanation = ""

            sibling = heading.find_next_sibling()
            while sibling and sibling.name not in ["h3", "h4"]:
                text = sibling.get_text(separator=" ", strip=True)

                # Look for options in lists
                if sibling.name in ["ul", "ol"]:
                    for idx, li in enumerate(sibling.find_all("li")):
                        li_text = clean_text(li.get_text())
                        opt_match = re.match(r'^[A-Da-d][.)]\s+(.+)', li_text)
                        if opt_match:
                            options.append(opt_match.group(1))
                        elif len(options) < 4 and li_text:
                            options.append(li_text)

                # Look for answer/explanation
                ans_match = re.search(r'[Aa]nswer[:\s]+([A-Da-d])', text)
                if ans_match and correct_option is None:
                    letter = ans_match.group(1).upper()
                    correct_option = ord(letter) - ord('A')
                    rest = text[ans_match.end():].strip()
                    if rest:
                        explanation = clean_text(rest)

                sibling = sibling.find_next_sibling()

            if len(options) == 4 and correct_option is not None:
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

    # Fallback: text-based parsing
    if not questions:
        content = soup.get_text(separator="\n")
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        i = 0
        while i < len(lines):
            line = lines[i]
            q_match = re.match(r'^(\d+)[.)]\s+(.+)', line)
            if not q_match:
                i += 1
                continue

            stem_parts = [clean_text(q_match.group(2))]
            i += 1
            while i < len(lines) and not re.match(r'^[A-Da-d][.)]\s+', lines[i]):
                if re.match(r'^\d+[.)]\s+', lines[i]):
                    break
                stem_parts.append(clean_text(lines[i]))
                i += 1

            stem = " ".join(p for p in stem_parts if p)
            options: list[str] = []
            while i < len(lines) and len(options) < 4:
                opt = re.match(r'^[A-Da-d][.)]\s+(.+)', lines[i])
                if opt:
                    options.append(clean_text(opt.group(1)))
                    i += 1
                else:
                    break

            if len(options) != 4:
                continue

            correct_option = None
            explanation = ""
            while i < len(lines):
                ans = re.search(r'[Aa]nswer[:\s]+([A-Da-d])', lines[i])
                if ans:
                    correct_option = ord(ans.group(1).upper()) - ord('A')
                    rest = lines[i][ans.end():].strip()
                    if rest:
                        explanation = clean_text(rest)
                    i += 1
                    while i < len(lines) and not re.match(r'^\d+[.)]\s+', lines[i]):
                        if lines[i]:
                            explanation = (explanation + " " + clean_text(lines[i])).strip()
                        i += 1
                    break
                if re.match(r'^\d+[.)]\s+', lines[i]):
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
