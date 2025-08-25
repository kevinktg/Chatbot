import json
from pathlib import Path
from typing import Optional, List

import typer
from rich import print

from .config import settings, Settings
from .ingest.pdf import extract_pdf
from .ingest.json_ingest import ingest_json
from .ingest.normalize import normalize_documents, save_documents
from .chunk.chonkie import chonkie_chunk
from .embed.embedder import EmbeddingRunner
from .index.faiss_store import FaissStore
from .api import app as fastapi_app  # noqa: F401  # enables `uvicorn training.api:app`

app = typer.Typer(help="AI-WA Training CLI")

# Optional import of local cloned Chonkie SDK
_HAS_CHONKIE = False
try:
    import sys
    from pathlib import Path as _P

    ROOT = _P(__file__).resolve().parents[1]
    CHONKIE_PATH = ROOT.parent / "chonkie"
    if (CHONKIE_PATH / "src").exists():
        sys.path.insert(0, str(CHONKIE_PATH / "src"))
    from chonkie.chunker.recursive import RecursiveChunker  # type: ignore
    _HAS_CHONKIE = True
except Exception:
    _HAS_CHONKIE = False


@app.command("ingest")
def ingest_cmd(
    pdf: Optional[Path] = typer.Option(None, help="Path to a PDF file or directory"),
    json_path: Optional[Path] = typer.Option(None, "--json", help="Path to JSON file"),
    out_path: Path = typer.Option(settings.data_interim / "documents.jsonl", help="Output unified docs JSONL"),
):
    """
    Ingest PDF and/or JSON into a unified document schema (JSONL).
    """
    docs = []

    if pdf:
        pdfs: List[Path] = []
        if pdf.is_dir():
            pdfs = sorted([p for p in pdf.glob("*.pdf")])
        elif pdf.is_file():
            pdfs = [pdf]
        else:
            raise typer.BadParameter("PDF path is not a file or directory")

        for p in pdfs:
            print(f"[cyan]Extracting PDF:[/cyan] {p}")
            texts = extract_pdf(p)
            docs.extend(normalize_documents(source=str(p), items=texts, doc_type="pdf"))

    if json_path:
        print(f"[cyan]Ingesting JSON:[/cyan] {json_path}")
        items = ingest_json(json_path)
        docs.extend(normalize_documents(source=str(json_path), items=items, doc_type="json"))

    if not docs:
        print("[yellow]No input provided. Use --pdf and/or --json.[/yellow]")
        raise typer.Exit(code=1)

    save_documents(docs, out_path)
    print(f"[green]Saved unified documents to[/green] {out_path}")


@app.command("chunk")
def chunk_cmd(
    in_path: Path = typer.Option(settings.data_interim / "documents.jsonl"),
    out_path: Path = typer.Option(settings.data_processed / "chunks.jsonl"),
    chunk_size: int = typer.Option(settings.chunk_size),
    chunk_overlap: int = typer.Option(settings.chunk_overlap),
    min_chunk_size: int = typer.Option(settings.min_chunk_size),
    respect_headings: bool = typer.Option(settings.respect_headings),
    engine: str = typer.Option("lite", help="lite | chonkie"),
):
    """
    Chunk unified documents using either the in-repo lite chunker or the cloned Chonkie SDK.
    """
    if not in_path.exists():
        print(f"[red]Input not found:[/red] {in_path}")
        raise typer.Exit(code=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if engine == "chonkie":
        if not _HAS_CHONKIE:
            print("[red]Chonkie SDK not available. Falling back to lite.[/red]")
        else:
            # Use Chonkie RecursiveChunker across concatenated text preserving starts
            print("[cyan]Chunking with Chonkie SDK (RecursiveChunker)...[/cyan]")
            from itertools import accumulate

            # Load docs
            import json as _json
            docs = []
            with in_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    docs.append(_json.loads(line))

            rc = RecursiveChunker(chunk_size=chunk_size, overlap=chunk_overlap, respect_headings=respect_headings)
            with out_path.open("w", encoding="utf-8") as fout:
                for d in docs:
                    text = d.get("content", "")
                    doc_id = d.get("id")
                    source = d.get("source", "")
                    pieces = rc.chunk(text)
                    start = 0
                    for idx, piece in enumerate(pieces):
                        end = start + len(piece)
                        obj = {
                            "id": f"{doc_id}:{idx}",
                            "doc_id": doc_id,
                            "source": source,
                            "start": start,
                            "end": end,
                            "text": piece,
                            "meta": d.get("meta", {}),
                        }
                        fout.write(_json.dumps(obj, ensure_ascii=False) + "\n")
                        start = max(0, end - chunk_overlap)
            print(f"[green]Saved chunks to[/green] {out_path}")
            return

    # Default lite engine
    print("[cyan]Chunking with lite engine...[/cyan]")
    chonkie_chunk(
        in_path=in_path,
        out_path=out_path,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
        respect_headings=respect_headings,
    )
    print(f"[green]Saved chunks to[/green] {out_path}")


@app.command("embed")
def embed_cmd(
    in_path: Path = typer.Option(settings.data_processed / "chunks.jsonl"),
    out_path: Path = typer.Option(settings.data_processed / "embeddings.npy"),
    uuids_out: Path = typer.Option(settings.data_processed / "chunk_ids.jsonl"),
    model: str = typer.Option(settings.embed_model, help="bge-small-en | bge-base-en | e5-small | e5-base"),
    device: str = typer.Option(settings.device, help="auto|cpu|cuda"),
    batch_size: int = typer.Option(settings.embed_batch_size),
    normalize: bool = typer.Option(settings.normalize_embeddings),
):
    """
    Compute embeddings for chunks and save .npy vectors + JSONL of chunk metadata (uuid order preserved).
    """
    if not in_path.exists():
        print(f"[red]Input not found:[/red] {in_path}")
        raise typer.Exit(code=1)

    runner = EmbeddingRunner(model_name=model, device=device, batch_size=batch_size, normalize=normalize)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    uuids_out.parent.mkdir(parents=True, exist_ok=True)

    print("[cyan]Embedding chunks...[/cyan]")
    runner.run(in_path=in_path, vectors_out=out_path, ids_out=uuids_out)
    print(f"[green]Saved embeddings to[/green] {out_path}")
    print(f"[green]Saved chunk ids to[/green] {uuids_out}")


@app.command("index")
def index_cmd(
    vectors_path: Path = typer.Option(settings.data_processed / "embeddings.npy"),
    ids_path: Path = typer.Option(settings.data_processed / "chunk_ids.jsonl"),
    index_dir: Path = typer.Option(settings.index_dir),
    metric: str = typer.Option(settings.faiss_metric, help="cosine|l2"),
    faiss_type: str = typer.Option(settings.faiss_type, help="flat|ivf"),
    nlist: int = typer.Option(settings.faiss_nlist, help="IVF lists"),
):
    """
    Build FAISS index from vectors and ids.
    """
    index_dir.mkdir(parents=True, exist_ok=True)
    print("[cyan]Building FAISS index...[/cyan]")
    FaissStore.build(
        vectors_path=vectors_path,
        ids_path=ids_path,
        index_dir=index_dir,
        metric=metric,
        index_type=faiss_type,
        nlist=nlist,
    )
    print(f"[green]FAISS index saved to[/green] {index_dir}")


@app.command("search")
def search_cmd(
    query: str = typer.Argument(..., help="Search query"),
    k: int = typer.Option(settings.top_k, "--k"),
    index_dir: Path = typer.Option(settings.index_dir),
    model: str = typer.Option(settings.embed_model),
    device: str = typer.Option(settings.device),
):
    """
    Ad-hoc search from CLI using the built FAISS index.
    """
    store = FaissStore.load(index_dir)
    runner = EmbeddingRunner(model_name=model, device=device)
    q_vec = runner.encode_text(query)
    results = store.search(q_vec, top_k=k)

    print("[bold cyan]Results[/bold cyan]")
    for r in results:
        print(json.dumps(r, ensure_ascii=False))


@app.command("query")
def query_cmd(
    question: str = typer.Argument(..., help="Question to ask (e.g., 'How much is the breakfast wrap?')"),
    k: int = typer.Option(settings.top_k, "--k", help="Top-k passages to retrieve"),
    index_dir: Path = typer.Option(settings.index_dir, help="Directory containing FAISS index and metadata"),
    model: str = typer.Option(settings.embed_model, help="Embedding model (name/shortcut)"),
    device: str = typer.Option(settings.device, help="Device: auto|cpu|cuda"),
    ids_path: Path = typer.Option(settings.data_processed / "chunk_ids.jsonl", help="Chunk ids JSONL to reconstruct source text"),
):
    """
    Simple local Q&A: retrieve top-k relevant chunks and print structured answers
    for price ('how much'), dietary filters, and recommendations.
    This is purely retrieval (no LLM generation) so it runs fully local.
    """
    # Load FAISS and embedder
    store = FaissStore.load(index_dir)
    runner = EmbeddingRunner(model_name=model, device=device)

    # Encode the question
    q_vec = runner.encode_text(question)
    hits = store.search(q_vec, top_k=k)

    # Load id -> minimal metadata (doc link if available)
    id_lookup = {}
    if ids_path.exists():
        with ids_path.open("r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    # Some pipelines store {"id": "..."} only; keep flexible
                    _id = obj.get("id") or obj.get("uuid") or obj.get("chunk_id")
                    if _id:
                        id_lookup[_id] = obj
                except Exception:
                    continue

    print("[bold cyan]Top results[/bold cyan]")
    answers = []
    for h in hits:
        # h is expected to contain: id, score, and stored metadata including "text"
        # FaissStore typically returns: {"id": ..., "score": float, "text": "...", "meta": {...}}
        print(json.dumps(h, ensure_ascii=False))
        answers.append(h)

    # Lightweight heuristics to surface structured signals:
    # 1) Price extraction
    import re
    price_pattern = re.compile(r"\$?\s*(\d{1,3}(?:[.,]\d{2})?)")

    prices = []
    dietary_flags = []
    recs = []

    for h in answers:
        text = (h.get("text") or "").strip()
        meta = h.get("meta") or {}
        # Price
        for m in price_pattern.finditer(text):
            # Normalize to $X.XX string
            val = m.group(1).replace(",", ".")
            # Heuristic sanity check: skip unrealistic values (e.g., years)
            try:
                f = float(val)
                if 0.5 <= f <= 1000:
                    prices.append(f"${f:.2f}")
            except Exception:
                pass
        # Dietary
        # Try a few fields commonly present in this repo's normalized items
        for key in ("primary_dietary_flag", "all_dietary_flags", "dietary", "tags"):
            v = meta.get(key)
            if isinstance(v, str) and v:
                dietary_flags.append(v)
            elif isinstance(v, list) and v:
                dietary_flags.extend([str(x) for x in v])

        # Recommendations: just collect top texts for now
        if text:
            recs.append(text)

    # Deduplicate while preserving order
    def _dedup(seq):
        seen = set()
        out = []
        for x in seq:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    prices = _dedup(prices)
    dietary_flags = _dedup(dietary_flags)
    recs = _dedup(recs)

    print("\n[bold green]Heuristic answers[/bold green]")
    if prices:
        print(f"[cyan]Possible prices:[/cyan] {prices[:5]}")
    else:
        print("[yellow]No explicit price values detected in top results.[/yellow]")

    if dietary_flags:
        print(f"[cyan]Dietary flags seen:[/cyan] {dietary_flags[:10]}")
    else:
        print("[yellow]No dietary flags detected in top results.[/yellow]")

    if recs:
        print("[cyan]Recommendations (top passages):[/cyan]")
        for t in recs[:min(5, len(recs))]:
            print(f"- {t[:300]}{'...' if len(t) > 300 else ''}")
    else:
        print("[yellow]No passages found for recommendations.[/yellow]")


@app.command("parity")
def parity_cmd(
    pdf: Path = typer.Argument(..., help="Path to a PDF to compare chunkers on"),
    out_dir: Path = typer.Option(Path("data/processed/parity"), help="Output directory for parity artifacts"),
    chunk_size: int = typer.Option(settings.chunk_size),
    chunk_overlap: int = typer.Option(settings.chunk_overlap),
    min_chunk_size: int = typer.Option(settings.min_chunk_size),
    respect_headings: bool = typer.Option(settings.respect_headings),
):
    """
    Run a parity test: our lite chunker vs Chonkie SDK (if available).
    Produces parity_report.json with summary stats and saves both chunk JSONLs.
    """
    from .chunk.parity import run_parity_on_pdf

    report, report_path = run_parity_on_pdf(
        pdf_path=pdf,
        out_dir=out_dir,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        min_chunk_size=min_chunk_size,
        respect_headings=respect_headings,
    )
    print("[bold cyan]Parity report[/bold cyan]")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[green]Saved report to[/green] {report_path}")

if __name__ == "__main__":
    app()