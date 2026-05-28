from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RetrievedChunk:
    chunk_id: str
    text: str
    metadata: dict
    dense_rank: int | None = None
    sparse_rank: int | None = None
    rrf_score: float = 0.0
    dense_similarity: float | None = None
    retrieval_score: float = 0.0
    merged_chunk_ids: list[str] | None = None
