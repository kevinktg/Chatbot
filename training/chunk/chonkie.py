from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, List, Dict, Any, Tuple


@dataclass
class Chunk:
    id: str
    doc_id: str
    source: str
    start: int
    end: int
    text: str
    meta: Dict[str, Any]


HEADING_RE = re.compile(r"^\s*(#{1,6}\s+.+|[A-Z][A-Z0-9 \-_/]{4,}|[0-9]+\.[\s\S]{0,80})\s*$")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def _is_heading(line: str) -> bool:
    # Heuristic: markdown headings, loud uppercase lines, or numbered headings
    if len(line.strip()) < 3:
        return False
    return bool(HEADING_RE.match(line.strip()))


def _split_sentences(text: str) -> List[str]:
    # Simple sentence split; avoids heavy deps for tiny datasets
    text = text.strip()
    if not text:
        return []
    return SENTENCE_SPLIT.split(text)


def _window_pack(sentences: List[str], chunk_size: int, overlap: int, min_chunk_size: int) -> List[str]:
    chunks: List[str] = []
    i = 0
    while i < len(sentences):
        cur: List[str] = []
        total = 0
        j = i
        while j < len(sentences) and total + len(sentences[j]) <= chunk_size:
            cur.append(sentences[j])
            total += len(sentences[j]) + 1
            j += 1

        if not cur and i < len(sentences):
            # single very long sentence; force cut
            s = sentences[i]
            cur = [s[:chunk_size]]
            remainder = s[chunk_size:]
            if remainder:
                sentences.insert(i + 1, remainder)

        chunk_text = " ".join(cur).strip()
        if len(chunk_text) >= min_chunk_size or not chunks:
            chunks.append(chunk_text)

        if j >= len(sentences):
            break

        # Step forward with overlap in characters approximated by sentences
        # Compute how many sentences to step back to approximate overlap
        back_chars = 0
        back_cnt = 0
        for t in reversed(cur):
            if back_chars >= overlap:
                break
            back_chars += len(t) + 1
            back_cnt += 1
        i = max(i + len(cur) - back_cnt, i + 1)

    return [c for c in chunks if c.strip()]


def _heading_aware_chunks(text: str, chunk_size: int, overlap: int, min_chunk_size: int, respect_headings: bool) -> List[str]:
    if not respect_headings:
        return _window_pack(_split_sentences(text), chunk_size, overlap, min_chunk_size)

    # Split by lines, segment on headings, then window-pack per segment
    lines = text.splitlines()
    segments: List[str] = []
    buf: List[str] = []
    for line in lines:
        if _is_heading(line) and buf:
            segments.append("\n".join(buf).strip())
            buf = [line]
        else:
            buf.append(line)
    if buf:
        segments.append("\n".join(buf).strip())

    chunks: List[str] = []
    for seg in segments:
        seg_sents = _split_sentences(seg)
        seg_chunks = _window_pack(seg_sents, chunk_size, overlap, min_chunk_size)
        chunks.extend(seg_chunks)

    return chunks


def chonkie_chunk(
    in_path: Path,
    out_path: Path,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    min_chunk_size: int = 200,
    respect_headings: bool = True,
) -> None:
    """
    Read unified documents JSONL, emit chunk JSONL with linkage to source docs.
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    count_docs = 0
    count_chunks = 0
    with in_path.open("r", encoding="utf-8") as fin, out_path.open("w", encoding="utf-8") as fout:
        for line in fin:
            if not line.strip():
                continue
            doc = json.loads(line)
            count_docs += 1
            text: str = doc.get("content", "")
            doc_id: str = doc.get("id")
            source: str = doc.get("source", "")
            meta = doc.get("meta", {})

            pieces = _heading_aware_chunks(
                text=text,
                chunk_size=chunk_size,
                overlap=chunk_overlap,
                min_chunk_size=min_chunk_size,
                respect_headings=respect_headings,
            )

            start = 0
            for idx, chunk_text in enumerate(pieces):
                end = start + len(chunk_text)
                chunk = {
                    "id": f"{doc_id}:{idx}",
                    "doc_id": doc_id,
                    "source": source,
                    "start": start,
                    "end": end,
                    "text": chunk_text,
                    "meta": meta,
                }
                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                count_chunks += 1
                # Move start with approximate overlap consideration
                start = max(0, end - chunk_overlap)

    # Optional: print summary to help debugging via CLI's rich print
    # but avoid stdout chatter here; CLI handles messaging.