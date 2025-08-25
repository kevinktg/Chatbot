from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

import faiss
import numpy as np


METRIC_MAP = {
    "cosine": faiss.METRIC_INNER_PRODUCT,
    "l2": faiss.METRIC_L2,
}


class FaissStore:
    """
    Lightweight FAISS index wrapper for local search.
    Stores:
      - index.faiss (FAISS binary)
      - ids.jsonl (id ordering)
      - meta.jsonl (optional metadata per id if provided)
      - norm flag for cosine (vectors should be normalized at embed time)
    """

    def __init__(self, index: faiss.Index, ids: List[str], index_dir: Path, metric: str = "cosine"):
        self.index = index
        self.ids = ids
        self.index_dir = index_dir
        self.metric = metric

    @staticmethod
    def _flat_index(dim: int, metric: str) -> faiss.Index:
        if metric == "cosine":
            # cosine -> inner product, expect normalized vectors
            return faiss.IndexFlatIP(dim)
        return faiss.IndexFlatL2(dim)

    @staticmethod
    def _ivf_index(dim: int, metric: str, nlist: int) -> faiss.Index:
        quantizer = FaissStore._flat_index(dim, metric)
        if metric == "cosine":
            return faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_INNER_PRODUCT)
        return faiss.IndexIVFFlat(quantizer, dim, nlist, faiss.METRIC_L2)

    @staticmethod
    def build(
        vectors_path: Path,
        ids_path: Path,
        index_dir: Path,
        metric: str = "cosine",
        index_type: str = "flat",
        nlist: int = 256,
    ) -> "FaissStore":
        if metric not in METRIC_MAP:
            raise ValueError(f"Unsupported metric: {metric}")
        vecs = np.load(vectors_path)
        if vecs.ndim != 2:
            raise ValueError("Embeddings array must be 2D")
        n, d = vecs.shape

        ids: List[str] = []
        with ids_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                ids.append(obj["id"])
        if len(ids) != n:
            raise ValueError(f"IDs count ({len(ids)}) != vectors count ({n})")

        if index_type == "flat":
            index = FaissStore._flat_index(d, metric)
            index.add(vecs.astype(np.float32))
        elif index_type == "ivf":
            index = FaissStore._ivf_index(d, metric, nlist)
            # IVF requires training
            if not index.is_trained:
                index.train(vecs.astype(np.float32))
            index.add(vecs.astype(np.float32))
        else:
            raise ValueError(f"Unsupported index_type: {index_type}")

        # Persist
        index_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_dir / "index.faiss"))
        with (index_dir / "ids.jsonl").open("w", encoding="utf-8") as f:
            for _id in ids:
                f.write(json.dumps({"id": _id}) + "\n")
        with (index_dir / "meta.json").open("w", encoding="utf-8") as f:
            json.dump({"metric": metric, "index_type": index_type, "dim": d, "count": n}, f)

        return FaissStore(index=index, ids=ids, index_dir=index_dir, metric=metric)

    @staticmethod
    def load(index_dir: Path) -> "FaissStore":
        index = faiss.read_index(str(index_dir / "index.faiss"))
        ids: List[str] = []
        with (index_dir / "ids.jsonl").open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                ids.append(json.loads(line)["id"])
        meta_path = index_dir / "meta.json"
        metric = "cosine"
        if meta_path.exists():
            with meta_path.open("r", encoding="utf-8") as f:
                meta = json.load(f)
                metric = meta.get("metric", "cosine")
        return FaissStore(index=index, ids=ids, index_dir=index_dir, metric=metric)

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> List[Dict[str, Any]]:
        if query_vec.ndim == 1:
            query_vec = query_vec.reshape(1, -1)
        D, I = self.index.search(query_vec.astype(np.float32), top_k)
        # Convert distances to similarity scores
        sims = D[0].tolist()
        idxs = I[0].tolist()
        results: List[Dict[str, Any]] = []
        for rank, (i, score) in enumerate(zip(idxs, sims), start=1):
            if i == -1:
                continue
            results.append(
                {
                    "rank": rank,
                    "id": self.ids[i],
                    "score": float(score),
                }
            )
        return results