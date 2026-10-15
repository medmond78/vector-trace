"""Count vector-plot pages vs embedded-image pages in PDFs.

Usage: python check_pdf_vectors.py file_or_folder [...]
Needs: pip install pymupdf
"""
import sys
from pathlib import Path

import pymupdf as fitz

MIN_PATHS = 50        # shortcut: text pages have few paths (rules, underlines); tune if results look off
MIN_IMAGE_FRAC = 0.05  # ignore logos and icons below 5% of the page area


def classify(page):
    paths = len(page.get_drawings())
    page_area = page.rect.width * page.rect.height
    img_area = sum(fitz.Rect(i["bbox"]).get_area() for i in page.get_image_info())
    return paths >= MIN_PATHS, img_area / page_area >= MIN_IMAGE_FRAC


def main(args):
    files = []
    for a in args:
        p = Path(a)
        files += sorted(p.rglob("*.pdf")) if p.is_dir() else [p]
    print(f"{'file':50} {'pages':>5} {'vector':>6} {'image':>5} {'both':>4}")
    for f in files:
        try:
            with fitz.open(f) as doc:
                flags = [classify(pg) for pg in doc]
        except Exception as e:
            print(f"{f.name[:50]:50} ERROR: {e}")
            continue
        vec = sum(v and not i for v, i in flags)
        img = sum(i and not v for v, i in flags)
        both = sum(v and i for v, i in flags)
        print(f"{f.name[:50]:50} {len(flags):5} {vec:6} {img:5} {both:4}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
