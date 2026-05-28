from __future__ import annotations

import json
from pathlib import Path

from pipeline.chunker import ChunkRecord
from runtime.phase_5_retrieval.models import RetrievedChunk


class ChunkIndex:
    def __init__(self, chunks_path: Path) -> None:
        self._by_id: dict[str, RetrievedChunk] = {}
        self._load(chunks_path)

    def _load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(f"Missing chunks index: {path}. Run: python -m jobs.ingest")
        with path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                meta = dict(row.get("metadata") or {})
                self._by_id[row["chunk_id"]] = RetrievedChunk(
                    chunk_id=row["chunk_id"],
                    text=row["text"],
                    metadata=meta,
                )

    def get(self, chunk_id: str) -> RetrievedChunk | None:
        return self._by_id.get(chunk_id)

    def wrap(self, chunk_id: str, **scores) -> RetrievedChunk | None:
        base = self._by_id.get(chunk_id)
        if not base:
            return None
        return RetrievedChunk(
            chunk_id=base.chunk_id,
            text=base.text,
            metadata=base.metadata,
            **scores,
        )

    @property
    def count(self) -> int:
        return len(self._by_id)
