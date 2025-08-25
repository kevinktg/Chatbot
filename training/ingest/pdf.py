from pathlib import Path
from typing import List

from PyPDF2 import PdfReader


def extract_pdf(path: Path) -> List[str]:
    """
    Extract text from a PDF file into a list of page-level strings.
    Basic cleanup is applied; downstream chunker will refine further.
    """
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    reader = PdfReader(str(path))
    pages: List[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        # Normalize whitespace
        text = " ".join(text.replace("\xa0", " ").split())
        if text.strip():
            pages.append(f"[PAGE {i+1}] {text}")
    return pages