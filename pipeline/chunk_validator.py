from __future__ import annotations

from pipeline.chunker import ChunkRecord
from pipeline.config import ChunkingConfig


class ChunkValidationError(Exception):
    pass


def validate_chunks(chunks: list[ChunkRecord], cfg: ChunkingConfig) -> list[ChunkRecord]:
    """§4.8 quality checks — fail build on critical errors."""
    if not chunks:
        raise ChunkValidationError("No chunks produced")

    seen_ids: set[str] = set()
    validated: list[ChunkRecord] = []
    schemes_with_chunks: set[str] = set()

    for chunk in chunks:
        if not chunk.text.strip():
            continue
        if chunk.token_count > cfg.hard_max_tokens:
            raise ChunkValidationError(
                f"Chunk {chunk.chunk_id} exceeds {cfg.hard_max_tokens} tokens ({chunk.token_count})"
            )
        url = chunk.metadata.get("source_url")
        if not url:
            raise ChunkValidationError(f"Chunk {chunk.chunk_id} missing source_url")
        if chunk.chunk_id in seen_ids:
            raise ChunkValidationError(f"Duplicate chunk_id: {chunk.chunk_id}")
        seen_ids.add(chunk.chunk_id)
        schemes_with_chunks.add(chunk.metadata.get("scheme_id", ""))
        validated.append(chunk)

    if not validated:
        raise ChunkValidationError("All chunks were empty after validation")

    return validated
