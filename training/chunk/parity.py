from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import List, Dict, Any, Tuple

from .chonkie import chonkie_chunk  # our lite chunker
from ..ingest.normalize import Document
from ..ingest.pdf import extract_pdf

# Try to import local cloned Chonkie SDK
try:
    import sys
    ROOT = Path(__file__).resolve().parents[2]
    CHONKIE_PATH = ROOT / "chonkie"
    if (CHONKIE_PATH / "src").exists():
        sys.path.insert(0, str(CHONKIE_PATH / "src"))
    from chonkie.chunker.recursive import RecursiveChunker  # type: ignore
    HAS_CHONKIE = True
except Exception:
    HAS_CHONKIE = False


@dataclass
class ParityStats:
    chunks: int
    mean_len: float
    stdev_len: float
    min_len: int
    max_len: int
    approx_overlap: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunks": self.chunks,
            "mean_len": round(self.mean_len, 2),
            "stdev_len": round(self.stdev_len, 2),
            "min_len": self.min_len,
            "max_len": self.max_len,
            "approx_overlap": round(self.approx_overlap, 2),
        }


def _load_chunks_jsonl(path: Path) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            out.append(json.loads(line))
    return out


def _stats_for(chunks: List[Dict[str, Any]]) -> ParityStats:
    lens = [len(c.get("text", "")) for c in chunks]
    if not lens:
        return ParityStats(0, 0, 0, 0, 0, 0)
    # Approx overlap: average of max(0, prev_end - start)
    approx_overlaps: List[int] = []
    prev_end = None
    for c in chunks:
        start = c.get("start", 0)
        if prev_end is not None:
            approx_overlaps.append(max(0, prev_end - start))
        prev_end = c.get("end", 0)
    approx_overlap = mean(approx_overlaps) if approx_overlaps else 0.0
    mu = mean(lens)
    # sample stdev
    if len(lens) > 1:
        stdev = math.sqrt(sum((x - mu) ** 2 for x in lens) / (len(lens) - 1))
    else:
        stdev = 0.0
    return ParityStats(
        chunks=len(lens),
        mean_len=mu,
        stdev_len=stdev,
        min_len=min(lens),
        max_len=max(lens),
        approx_overlap=approx_overlap,
    )


def run_parity_on_pdf(
    pdf_path: Path,
    out_dir: Path,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    min_chunk_size: int = 200,
    respect_headings: bool = True,
) -> Tuple[Dict[str, Any], Path]:
    """
    Compare our lite chonkie vs local Chonkie SDK (recursive) on the same PDF.
    Returns (report_dict, report_path).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # 1) Build a temporary unified docs JSONL for the PDF
    pages = extract_pdf(pdf_path)
    docs = [Document.from_text(str(pdf_path), "pdf", p, {"page": i + 1}) for i, p in enumerate(pages)]
    docs_path = out_dir / "tmp_docs.jsonl"
    with docs_path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(d.__dict__, ensure_ascii=False) + "\n")

    # 2) Our lite chonkie
    lite_chunks_path = out_dir / "lite_chunks.jsonl"
    chonkie_chunk(
        in_path=docs_path,
        out_path=lite_chunks_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
        respect_headings=respect_headings,
    )
    lite_chunks = _load_chunks_jsonl(lite_chunks_path)
    lite_stats = _stats_for(lite_chunks)

    # 3) Chonkie SDK recursive chunker (if available)
    chonk_chunks_path = out_dir / "chonkie_chunks.jsonl"
    chonk_stats: ParityStats | None = None
    if HAS_CHONKIE:
        # Using RecursiveChunker with similar parameters
        rc = RecursiveChunker(
            chunk_size=chunk_size,
            overlap=chunk_overlap,
            respect_headings=respect_headings,
        )
        combined_text = "\n".join(pages)
        chonk_pieces = rc.chunk(combined_text)
        # Normalize to our schema
        with chonk_chunks_path.open("w", encoding="utf-8") as f:
            start = 0
            for i, text in enumerate(chonk_pieces):
                end = start + len(text)
                obj = {
                    "id": f"chonkie:{i}",
                    "doc_id": "chonkie",
                    "source": str(pdf_path),
                    "start": start,
                    "end": end,
                    "text": text,
                    "meta": {},
                }
                f.write(json.dumps(obj, ensure_ascii=False) + "\n")
                start = max(0, end - chunk_overlap)
        chonk_chunks = _load_chunks_jsonl(chonk_chunks_path)
        chonk_stats = _stats_for(chonk_chunks)

    # 4) Build report
    report = {
        "pdf": str(pdf_path),
        "has_chonkie_sdk": HAS_CHONKIE,
        "params": {
            "chunk_size": chunk_size,
            "chunk_overlap": chunk_overlap,
            "min_chunk_size": min_chunk_size,
            "respect_headings": respect_headings,
        },
        "lite": lite_stats.to_dict(),
        "chonkie": chonk_stats.to_dict() if chonk_stats else None,
    }
    report_path = out_dir / "parity_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    return report, report_path