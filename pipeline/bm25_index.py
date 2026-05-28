from __future__ import annotations

import json
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

from pipeline.chunker import ChunkRecord


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+%?|[%₹]|\d+(?:\.\d+)?", text.lower())


def build_bm25_index(chunks: list[ChunkRecord], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    corpus = [_tokenize(c.text) for c in chunks]
    bm25 = BM25Okapi(corpus)
    chunk_ids = [c.chunk_id for c in chunks]

    with (out_dir / "bm25.pkl").open("wb") as f:
        pickle.dump(bm25, f)
    (out_dir / "chunk_ids.json").write_text(
        json.dumps(chunk_ids, indent=2),
        encoding="utf-8",
    )


def load_bm25_index(out_dir: Path) -> tuple[BM25Okapi, list[str]]:
    with (out_dir / "bm25.pkl").open("rb") as f:
        bm25 = pickle.load(f)
    chunk_ids = json.loads((out_dir / "chunk_ids.json").read_text(encoding="utf-8"))
    return bm25, chunk_ids


def search_bm25(
    bm25: BM25Okapi,
    chunk_ids: list[str],
    query: str,
    top_k: int,
) -> list[tuple[str, float]]:
    tokens = _tokenize(query)
    if not tokens:
        return []
    scores = bm25.get_scores(tokens)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    results: list[tuple[str, float]] = []
    for idx, score in ranked[:top_k]:
        if score <= 0:
            continue
        results.append((chunk_ids[idx], float(score)))
    return results
