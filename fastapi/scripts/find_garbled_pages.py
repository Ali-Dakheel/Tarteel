"""Find garbled pages in all PDFs and show which pages and what type of garbling."""
import re
from pathlib import Path
import pdfplumber

DATA_DIR = Path(__file__).parent.parent / "data"


def word_garble_ratio(text: str) -> float:
    """
    Detect two garbling patterns per word:
    1. Doubled chars: >40% of adjacent letter pairs identical  (SSeeccttiioonn)
    2. Mid-word uppercase: uppercase letter not at position 0  (tSryosdteumct, IAn)
    """
    garbled = 0
    total = 0
    for word in text.split():
        # Strip punctuation for analysis
        clean = re.sub(r"[^A-Za-z]", "", word)
        if len(clean) < 4:
            continue
        total += 1
        # Pattern 1: doubled chars
        doubled = sum(1 for a, b in zip(clean, clean[1:]) if a == b) / len(clean)
        # Pattern 2: mid-word uppercase (position > 0, not all-caps acronym)
        mid_upper = any(c.isupper() for c in clean[1:]) and not clean.isupper()
        if doubled > 0.40 or mid_upper:
            garbled += 1
    return garbled / total if total else 0.0


for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
    print(f"\n{'=' * 70}")
    print(f"PDF: {pdf_path.name}")
    garbled_pages = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
                if len(text.split()) < 20:
                    continue
                ratio = word_garble_ratio(text)
                if ratio > 0.02:  # any page with >2% garbled words
                    label = "HEAVY" if ratio > 0.20 else "PARTIAL"
                    sample = " ".join(text.split()[:12])[:100]
                    print(f"  p{i:<4}  {label} ({ratio:.0%})  →  {sample}")
                    garbled_pages.append(i)
            except Exception:
                continue
    if garbled_pages:
        print(f"  → {len(garbled_pages)} garbled pages: {garbled_pages}")
    else:
        print("  → No garbled pages found ✓")
