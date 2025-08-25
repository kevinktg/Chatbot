from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from .config import settings
from .embed.embedder import EmbeddingRunner
from .index.faiss_store import FaissStore


app = FastAPI(title="AI-WA Training Query API")


class QueryRequest(BaseModel):
    query: str
    k: int | None = None


class QueryHit(BaseModel):
    rank: int
    id: str
    score: float
    text: str | None = None
    source: str | None = None


class QueryResponse(BaseModel):
    hits: List[QueryHit]


# Lazy singletons
_store: FaissStore | None = None
_runner: EmbeddingRunner | None = None
_chunk_lookup_path: Path = settings.data_processed / "chunks.jsonl"
_chunk_text_by_id: dict[str, dict] | None = None


def _ensure_store() -> FaissStore:
    global _store
    if _store is None:
        if not (settings.index_dir / "index.faiss").exists():
            raise HTTPException(status_code=400, detail="Index not built. Run `aiwa index` first.")
        _store = FaissStore.load(settings.index_dir)
    return _store


def _ensure_runner() -> EmbeddingRunner:
    global _runner
    if _runner is None:
        _runner = EmbeddingRunner(model_name=settings.embed_model, device=settings.device)
    return _runner


def _ensure_chunk_lookup() -> dict[str, dict]:
    global _chunk_text_by_id
    if _chunk_text_by_id is None:
        if not _chunk_lookup_path.exists():
            raise HTTPException(status_code=400, detail="Chunks not found. Run `aiwa chunk` first.")
        _chunk_text_by_id = {}
        with _chunk_lookup_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                _chunk_text_by_id[obj["id"]] = obj
    return _chunk_text_by_id


@app.post("/query", response_model=QueryResponse)
def query(req: QueryRequest) -> QueryResponse:
    store = _ensure_store()
    runner = _ensure_runner()
    chunk_map = _ensure_chunk_lookup()

    q_vec: np.ndarray = runner.encode_text(req.query)
    k = req.k or settings.top_k
    raw_hits = store.search(q_vec, top_k=k)

    hits: List[QueryHit] = []
    for h in raw_hits:
        cid = h["id"]
        meta = chunk_map.get(cid, {})
        hits.append(
            QueryHit(
                rank=h["rank"],
                id=cid,
                score=h["score"],
                text=meta.get("text"),
                source=meta.get("source"),
            )
        )
    return QueryResponse(hits=hits)


@app.get("/healthz")
def health() -> dict:
    return {"status": "ok"}