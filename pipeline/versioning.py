from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schemes": {}, "corpus_version": 0}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)


def snapshot_index(
    index_dir: Path,
    snapshot_dir: Path,
    corpus_version: int,
    *,
    include_local_chroma: bool = False,
) -> Path:
    """§4.7 Keep last-good index snapshot before swap."""
    dest = snapshot_dir / f"v{corpus_version}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)
    names = ["bm25", "chunks.jsonl", "embeddings_manifest.json"]
    if include_local_chroma:
        names = ["chroma", *names]
    for name in names:
        src = index_dir / name
        if src.exists():
            if src.is_dir():
                shutil.copytree(src, dest / name)
            else:
                shutil.copy2(src, dest / name)
    return dest


def restore_snapshot(
    index_dir: Path,
    snapshot_dir: Path,
    version: int,
    *,
    include_local_chroma: bool = False,
) -> bool:
    src = snapshot_dir / f"v{version}"
    if not src.exists():
        return False
    names = ["bm25", "chunks.jsonl", "embeddings_manifest.json"]
    if include_local_chroma:
        names = ["chroma", *names]
    for name in names:
        s = src / name
        d = index_dir / name
        if d.exists():
            if d.is_dir():
                shutil.rmtree(d)
            else:
                d.unlink()
        if s.exists():
            if s.is_dir():
                shutil.copytree(s, d)
            else:
                shutil.copy2(s, d)
    return True


def record_ingest_run(
    manifest: dict[str, Any],
    *,
    chunk_count: int,
    corpus_version: int,
    embedding_model: str,
    skipped_cache: int,
) -> dict[str, Any]:
    manifest["corpus_version"] = corpus_version
    manifest["last_ingest_run"] = {
        "completed_at": _now_iso(),
        "chunk_count": chunk_count,
        "embedding_model": embedding_model,
        "skipped_embed_cache": skipped_cache,
    }
    return manifest
