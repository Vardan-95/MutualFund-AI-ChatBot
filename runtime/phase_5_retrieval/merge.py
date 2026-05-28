from __future__ import annotations

from runtime.phase_5_retrieval.models import RetrievedChunk


def merge_chunks_by_source_url(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Merge high-scoring chunks that share source_url into one context row."""
    if not chunks:
        return []

    by_url: dict[str, list[RetrievedChunk]] = {}
    order: list[str] = []
    for ch in chunks:
        url = str(ch.metadata.get("source_url") or "")
        if url not in by_url:
            order.append(url)
            by_url[url] = []
        by_url[url].append(ch)

    merged: list[RetrievedChunk] = []
    for url in order:
        group = by_url[url]
        if len(group) == 1:
            merged.append(group[0])
            continue
        group_sorted = sorted(
            group,
            key=lambda c: c.retrieval_score,
            reverse=True,
        )
        primary = group_sorted[0]
        texts = []
        seen: set[str] = set()
        for ch in group_sorted:
            t = ch.text.strip()
            if t and t not in seen:
                seen.add(t)
                texts.append(t)
        merged_ids = [c.chunk_id for c in group_sorted]
        merged.append(
            RetrievedChunk(
                chunk_id=primary.chunk_id,
                text="\n\n".join(texts),
                metadata=dict(primary.metadata),
                dense_rank=primary.dense_rank,
                sparse_rank=primary.sparse_rank,
                rrf_score=primary.rrf_score,
                dense_similarity=primary.dense_similarity,
                retrieval_score=primary.retrieval_score,
                merged_chunk_ids=merged_ids,
            )
        )
    merged.sort(key=lambda c: c.retrieval_score, reverse=True)
    return merged
