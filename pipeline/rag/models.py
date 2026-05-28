from __future__ import annotations



from dataclasses import dataclass, field



from runtime.phase_5_retrieval.models import RetrievedChunk



__all__ = ["RetrievedChunk", "RAGResponse"]





@dataclass

class RAGResponse:

    answer: str

    intent: str

    source_url: str | None

    content_captured_at: str | None

    corpus_version: int | None

    chunk_ids: list[str] = field(default_factory=list)

    refused: bool = False

    disclaimer: str = ""

    education_url: str | None = None

    intent_matched_by: str | None = None

    guardrail_flags: list[str] = field(default_factory=list)

