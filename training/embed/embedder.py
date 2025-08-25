from __future__ import annotations

import json
from pathlib import Path
from typing import List

import numpy as np
from tqdm import tqdm

from .models import load_embedder


class EmbeddingRunner:
    def __init__(self, model_name: str = "bge-small-en", device: str = "auto", batch_size: int = 64, normalize: bool = True):
        self.model_name = model_name
        self.device = None if device == "auto" else device
        self.batch_size = batch_size
        self.normalize = normalize
        self.model, self.dim = load_embedder(model_name)
        if self.device:
            try:
                self.model.to(self.device)
            except Exception:
                # Fallback to default device if move fails
                pass

    def _encode_batch(self, texts: List[str]) -> np.ndarray:
        embs = self.model.encode(
            texts,
            batch_size=self.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self.normalize,
            convert_to_numpy=True,
        )
        return embs.astype(np.float32)

    def run(self, in_path: Path, vectors_out: Path, ids_out: Path) -> None:
        texts: List[str] = []
        ids: List[str] = []

        with in_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = json.loads(line)
                ids.append(obj["id"])
                texts.append(obj["text"])

        vectors_out.parent.mkdir(parents=True, exist_ok=True)
        ids_out.parent.mkdir(parents=True, exist_ok=True)

        all_vecs: List[np.ndarray] = []
        for i in tqdm(range(0, len(texts), self.batch_size), desc="Embedding"):
            batch = texts[i : i + self.batch_size]
            vecs = self._encode_batch(batch)
            all_vecs.append(vecs)

        if all_vecs:
            mat = np.vstack(all_vecs)
        else:
            mat = np.zeros((0, self.dim), dtype=np.float32)

        np.save(vectors_out, mat)
        with ids_out.open("w", encoding="utf-8") as f:
            for _id in ids:
                f.write(json.dumps({"id": _id}) + "\n")

    def encode_text(self, text: str) -> np.ndarray:
        vec = self._encode_batch([text])
        return vec.astype(np.float32)