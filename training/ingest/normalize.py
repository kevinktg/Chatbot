from __future__ import annotations

import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


@dataclass
class Document:
    id: str
    source: str
    doc_type: str  # "pdf" | "json"
    content: str
    meta: Dict[str, Any]
    created_at: str

    @staticmethod
    def from_text(source: str, doc_type: str, content: str, meta: Optional[Dict[str, Any]] = None) -> "Document":
        return Document(
            id=str(uuid.uuid4()),
            source=source,
            doc_type=doc_type,
            content=content,
            meta=meta or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )


def normalize_documents(source: str, items: Iterable[Any], doc_type: str) -> List[Document]:
    """
    Normalize arbitrary input (PDF page strings, JSON objects) into Document records.
    - PDF ingest supplies a list[str], each representing a page text.
    - JSON ingest supplies a list[dict] (or value-wrapped).
    """
    docs: List[Document] = []
    for item in items:
        if isinstance(item, str):
            content = item
            meta = {"content_type": "text", "len": len(content)}
        elif isinstance(item, dict):
            # Keep compact body, full JSON in meta
            if "text" in item and isinstance(item["text"], str):
                content = item["text"]
            elif "body" in item and isinstance(item["body"], str):
                content = item["body"]
            else:
                # best-effort flatten
                content = json.dumps(item, ensure_ascii=False)
            meta = {"json": item, "len": len(content)}
        else:
            content = str(item)
            meta = {"content_type": "unknown", "len": len(content)}

        if not content.strip():
            continue

        docs.append(Document.from_text(source=source, doc_type=doc_type, content=content, meta=meta))
    return docs


def save_documents(docs: List[Document], out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for d in docs:
            f.write(json.dumps(asdict(d), ensure_ascii=False) + "\n")