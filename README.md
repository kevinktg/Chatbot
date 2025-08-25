# ai-wa-training

Low-resource training and retrieval pipeline for tiny-dataset bots (PDF/JSON ingestion, Chonkie-style chunking, embeddings, FAISS index, minimal query API). Designed for 12GB VRAM / 32GB RAM local rigs with optional CPU-only.

Features
- Ingest PDF(s) and JSON into a unified schema
- Chonkie-style semantic chunking (overlap, heading-aware)
- Embeddings via sentence-transformers (bge-small/e5-small selectable)
- FAISS local index (flat or IVF, CPU-friendly)
- Synthetic Q&A generation (optional) for tests
- Safety policy scaffolds and vertical refusal templates
- Minimal FastAPI query service with cosine similarity
- CLI for end-to-end: ingest → chunk → embed → index → serve

Quick Start
1) Place your PDF at data/raw/source.pdf (or multiple PDFs in data/raw/)
2) (Optional) Put JSON at data/raw/gf2025-main.json
3) Create and activate environment:

   Windows (PowerShell):
   python -m venv .venv
   .venv\Scripts\activate
   pip install -U pip
   pip install -e .

4) Build the index:
   python -m training.cli ingest --pdf data/raw/source.pdf --json data/raw/gf2025-main.json
   python -m training.cli chunk --chunker chonkie
   python -m training.cli embed --model bge-small-en
   python -m training.cli index --metric cosine --faiss-type flat

5) Serve:
   uvicorn training.api:app --host 0.0.0.0 --port 8000

6) Query:
   curl -X POST http://localhost:8000/query -H "Content-Type: application/json" -d "{\"query\":\"What services are included?\"}"

Repo Structure
- training/
  - __init__.py
  - cli.py            # CLI entrypoints
  - config.py         # Global settings and defaults
  - ingest/
    - __init__.py
    - pdf.py          # PDF extraction (pypdf)
    - json_ingest.py  # JSON ingestion
    - normalize.py    # Unify to Document schema
  - chunk/
    - __init__.py
    - chonkie.py      # Heading-aware semantic chunker
  - embed/
    - __init__.py
    - models.py       # bge/e5 loader
    - embedder.py     # batch embed
  - index/
    - __init__.py
    - faiss_store.py  # FAISS save/load/search
  - api.py            # FastAPI minimal server
  - safety/
    - __init__.py
    - policies.py     # vertical refusal templates
  - synth/
    - __init__.py
    - qa.py           # synthetic Q&A generator (optional)
- data/
  - raw/
    - source.pdf      # drop your PDF here
    - gf2025-main.json (optional)
  - interim/
  - processed/
  - index/
- tests/
- scripts/
  - download_example_pdf.py
- pyproject.toml
- requirements.txt
- .env.example
- .gitignore

Notes
- If your GPU VRAM is tight, set TRAINING_DEVICE=cpu in .env or use smaller embedding model.
- This scaffolds retrieval; fine-tuning is intentionally out-of-scope for now.
- Supports multiple PDFs; pass a folder to --pdf.