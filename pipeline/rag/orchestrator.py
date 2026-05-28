"""RAG orchestrator — delegates to runtime.phase_7_safety."""

from __future__ import annotations

from pipeline.rag.models import RAGResponse
from runtime.phase_7_safety.answer import answer as _answer


def run_query(
    query: str,
    *,
    thread_context: str | None = None,
) -> RAGResponse:
    return _answer(query, thread_context=thread_context)
