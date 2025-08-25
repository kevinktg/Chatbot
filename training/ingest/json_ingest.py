from pathlib import Path
from typing import Any, Dict, List, Union

import orjson


def _load_json(path: Path) -> Union[Dict[str, Any], List[Any]]:
    with path.open("rb") as f:
        return orjson.loads(f.read())


def ingest_json(path: Path) -> List[Dict[str, Any]]:
    """
    Load JSON or JSONL into a list of dicts. If it's a dict, wrap as single-item list.
    If it's a list, ensure items are dict-like.
    If it's JSONL, parse line by line.
    """
    if not path.exists():
        raise FileNotFoundError(f"JSON not found: {path}")

    if path.suffix.lower() == ".jsonl":
        items: List[Dict[str, Any]] = []
        with path.open("rb") as f:
            for line in f:
                if not line.strip():
                    continue
                obj = orjson.loads(line)
                if isinstance(obj, dict):
                    items.append(obj)
                else:
                    items.append({"value": obj})
        return items

    obj = _load_json(path)
    if isinstance(obj, dict):
        return [obj]
    if isinstance(obj, list):
        out: List[Dict[str, Any]] = []
        for x in obj:
            if isinstance(x, dict):
                out.append(x)
            else:
                out.append({"value": x})
        return out

    # Fallback: wrap as a string
    return [{"value": str(obj)}]