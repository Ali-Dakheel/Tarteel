"""Quick PDF quality diagnostic — run before/after ingestion to verify text extraction."""
import re
from pathlib import Path

import pdfplumber

DATA_DIR = Path(__file__).parent.parent / "data"


def check_pdf(pdf_path: Path) -> None:
    print(f"\n{'=' * 60}")
    print(f"PDF: {pdf_path.name}  ({pdf_path.stat().st_size / 1_000_000:.1f} MB)")

    total = 0
    skipped = 0
    short = 0
    garbled = 0
    total_words = 0
    sample_good: list[tuple[int, str]] = []
    sample_bad: list[tuple[int, str]] = []

    with pdfplumber.open(pdf_path) as pdf:
        total = len(pdf.pages)
        for i, page in enumerate(pdf.pages, start=1):
            try:
                text = page.extract_text() or ""
                words = text.split()
                wc = len(words)
                total_words += wc

                if wc < 20:
                    skipped += 1
                    continue

                if wc < 80:
                    short += 1

                # Detect doubled-character garbling pattern (e.g., "SSeeccttiioonn")
                garble_hits = re.findall(r"([A-Za-z])\1[A-Za-z]{1,3}([A-Za-z])\2", text)
                if len(garble_hits) > 3:
                    garbled += 1
                    if len(sample_bad) < 2:
                        sample_bad.append((i, text[:200]))
                else:
                    if len(sample_good) < 2 and i > 5:  # skip front matter
                        sample_good.append((i, text[:200]))

            except Exception as e:
                skipped += 1

    extracted = total - skipped
    avg_words = total_words // max(extracted, 1)

    print(f"  Pages total:     {total}")
    print(f"  Pages extracted: {extracted}  ({skipped} skipped — image/empty)")
    print(f"  Pages short:     {short}  (20-80 words, likely headers/figures)")
    print(f"  Pages garbled:   {garbled}  (doubled-char encoding issues)")
    print(f"  Avg words/page:  {avg_words}")
    print(f"  Total words:     {total_words:,}")

    if garbled > 0:
        print(f"\n  ⚠ GARBLED SAMPLES:")
        for page_num, snippet in sample_bad:
            print(f"    p{page_num}: {snippet[:150]!r}")

    print(f"\n  GOOD CONTENT SAMPLES:")
    for page_num, snippet in sample_good:
        print(f"    p{page_num}: {snippet[:150]!r}")


if __name__ == "__main__":
    pdfs = sorted(DATA_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"No PDFs found in {DATA_DIR}")
    else:
        for p in pdfs:
            check_pdf(p)
    print(f"\n{'=' * 60}")
    print("Done.")
