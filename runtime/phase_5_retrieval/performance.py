from __future__ import annotations

from phases.p2_compliance.refusal import performance_guard_message
from runtime.phase_5_retrieval.models import RetrievedChunk
from runtime.phase_5_retrieval.citation import select_citation


def performance_link_only_answer(
    chunks: list[RetrievedChunk],
    *,
    scheme_id: str | None,
    scheme_name: str | None = None,
    allowed_domains: list[str] | None = None,
) -> tuple[str, str | None, str | None]:
    """Link-only response for PERFORMANCE_REQUEST — no return synthesis."""
    cite = select_citation(
        chunks,
        scheme_id=scheme_id,
        allowed_domains=allowed_domains or ["groww.in"],
    )
    name = scheme_name
    if not name and chunks:
        name = str(chunks[0].metadata.get("scheme_name") or "this fund")
    if not name:
        name = "this fund"
    url = cite.source_url or ""
    if not url:
        return (
            "I do not calculate or compare returns. "
            "Please open the Groww page for the HDFC scheme you mean.",
            None,
            cite.content_captured_at,
        )
    return (
        performance_guard_message(name, url),
        url,
        cite.content_captured_at,
    )
