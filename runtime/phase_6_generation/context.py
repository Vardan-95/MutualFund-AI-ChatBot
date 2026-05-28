from __future__ import annotations

from pipeline.rag.answer_format import simplify_context_for_llm
from runtime.phase_5_retrieval.models import RetrievedChunk

_DEVELOPER_INSTRUCTIONS = (
    "Use only the CONTEXT blocks below. "
    "If CONTEXT is insufficient, say you cannot find it in the indexed sources "
    "and suggest the relevant allowlisted scheme URL from the Source URL metadata if available. "
    "Do not invent facts or links."
)


def pack_context(chunks: list[RetrievedChunk]) -> str:
    """§6.1 — chunk text with explicit Source URL headers."""
    parts: list[str] = []
    for i, ch in enumerate(chunks, start=1):
        url = str(ch.metadata.get("source_url") or "")
        scheme = str(ch.metadata.get("scheme_name") or "")
        section = str(ch.metadata.get("section_title") or ch.metadata.get("section_canonical") or "")
        captured = (
            ch.metadata.get("content_captured_at")
            or ch.metadata.get("source_last_updated")
            or ch.metadata.get("ingested_at")
            or ""
        )
        body = simplify_context_for_llm(ch.text)
        header = f"[{i}] Source URL: {url}"
        if scheme:
            header += f"\nScheme: {scheme}"
        if section:
            header += f"\nSection: {section}"
        if captured:
            header += f"\nContent captured: {captured}"
        parts.append(f"{header}\n---\n{body}")
    return "\n\n".join(parts)


def build_user_message(query: str, chunks: list[RetrievedChunk]) -> str:
    context = pack_context(chunks)
    return (
        f"{_DEVELOPER_INSTRUCTIONS}\n\n"
        f"CONTEXT:\n{context}\n\n"
        f"Question: {query}\n\n"
        "Reply in at most 3 short plain sentences. No markdown, tables, bullets, or URLs in the reply."
    )


def format_footer(date: str) -> str:
    if not date:
        return ""
    return f"Last updated from sources: {date}"
