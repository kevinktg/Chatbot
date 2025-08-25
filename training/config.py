import os
from pathlib import Path
from typing import Literal, Optional

from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    # Paths
    root_dir: Path = Field(default_factory=lambda: Path(os.getcwd()))
    data_raw: Path = Field(default_factory=lambda: Path("data/raw"))
    data_interim: Path = Field(default_factory=lambda: Path("data/interim"))
    data_processed: Path = Field(default_factory=lambda: Path("data/processed"))
    index_dir: Path = Field(default_factory=lambda: Path("data/index"))

    # Chunking
    chunker: Literal["chonkie"] = "chonkie"
    chunk_size: int = 800
    chunk_overlap: int = 150
    min_chunk_size: int = 200
    respect_headings: bool = True

    # Embeddings
    embed_model: Literal[
        "bge-small-en", "bge-base-en", "e5-small", "e5-base"
    ] = "bge-small-en"
    embed_batch_size: int = 64
    device: Literal["auto", "cpu", "cuda"] = os.getenv("TRAINING_DEVICE", "auto")  # auto picks cuda if available
    normalize_embeddings: bool = True

    # FAISS
    faiss_metric: Literal["cosine", "l2"] = "cosine"
    faiss_type: Literal["flat", "ivf"] = "flat"
    faiss_nlist: int = 256  # for IVF
    top_k: int = 5

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Synthetic Q&A
    synth_enabled: bool = False
    synth_per_chunk: int = 2

    # Safety / Policies
    vertical: Optional[Literal["food", "medical", "trades"]] = None

    def ensure_dirs(self) -> None:
        for d in [self.data_raw, self.data_interim, self.data_processed, self.index_dir]:
            Path(d).mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()