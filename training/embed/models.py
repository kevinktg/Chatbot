from typing import Tuple, Protocol, List
import os
import requests

from sentence_transformers import SentenceTransformer
import numpy as np


class EmbedderProtocol(Protocol):
    def encode(self, texts: List[str], batch_size: int = 32, show_progress_bar: bool = False,
               normalize_embeddings: bool = True, convert_to_numpy: bool = True):
        ...


class OllamaEmbedder:
    """
    Minimal adapter to use an Ollama embedding model with the same interface shape
    expected by EmbeddingRunner._encode_batch().

    It calls the local Ollama server:
      POST http://localhost:11434/api/embeddings
      body: {"model": "...", "prompt": "..."}
    """
    def __init__(self, model: str, dim: int | None = None, host: str | None = None):
        self.model = model
        self.host = host or os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self._dim = dim  # Optional manual override if you know the dimension

    def get_sentence_embedding_dimension(self) -> int:
        # If dimension not provided, we can discover by doing a tiny request once.
        if self._dim is None:
            try:
                r = requests.post(
                    f"{self.host}/api/embeddings",
                    json={"model": self.model, "prompt": "dimension probe"},
                    timeout=30,
                )
                r.raise_for_status()
                data = r.json()
                vec = data.get("embedding", [])
                self._dim = len(vec)
            except Exception:
                # Fallback to a common dimension; users can override if needed.
                self._dim = 768
        return self._dim

    def encode(self, texts: List[str], batch_size: int = 32, show_progress_bar: bool = False,
               normalize_embeddings: bool = True, convert_to_numpy: bool = True):
        embs: List[np.ndarray] = []
        for t in texts:
            r = requests.post(
                f"{self.host}/api/embeddings",
                json={"model": self.model, "prompt": t},
                timeout=120,
            )
            r.raise_for_status()
            data = r.json()
            vec = np.array(data["embedding"], dtype=np.float32)
            if normalize_embeddings and vec.size > 0:
                # L2 normalize
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
            embs.append(vec)
        mat = np.vstack(embs) if embs else np.zeros((0, self.get_sentence_embedding_dimension()), dtype=np.float32)
        return mat if convert_to_numpy else mat.tolist()


def load_embedder(model_name: str) -> Tuple[EmbedderProtocol, int]:
    """
    Load an embedding model and return (model_like, dim).

    Supports:
      - Local sentence-transformers by name shortcut (bge-small-en, e5-small, etc.)
      - Ollama via env EMBEDDING_BACKEND=ollama and EMBEDDING_MODEL
        Defaults: nomic-embed-text
    """
    backend = os.getenv("EMBEDDING_BACKEND", "").strip().lower()
    env_model = os.getenv("EMBEDDING_MODEL", "").strip()

    # Map short names to HuggingFace repos
    name_map = {
        "bge-small-en": "BAAI/bge-small-en-v1.5",
        "bge-base-en": "BAAI/bge-base-en-v1.5",
        "e5-small": "intfloat/e5-small-v2",
        "e5-base": "intfloat/e5-base-v2",
    }

    # Default: Ollama with nomic-embed-text as requested
    if backend == "ollama" or (backend == "" and (env_model.startswith("nomic") or env_model.startswith("mxbai") or env_model == "")):
        ollama_model = env_model or "nomic-embed-text"
        ollama = OllamaEmbedder(model=ollama_model)
        dim = ollama.get_sentence_embedding_dimension()
        return ollama, dim

    # Fallback to sentence-transformers
    repo = name_map.get(env_model or model_name, env_model or model_name)
    st_model = SentenceTransformer(repo)
    dim = st_model.get_sentence_embedding_dimension()
    return st_model, dim