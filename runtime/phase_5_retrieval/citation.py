from __future__ import annotations

import re
from dataclasses import dataclass

from phases.common.config_loader import load_sources_config
from runtime.phase_5_retrieval.models import RetrievedChunk

_WORD = re.compile(r"[a-z0-9]+", re.I)


@dataclass(frozen=True)
class CitationResult:
    source_url: str | None
    content_captured_at: str | None
    primary_chunk_id: str | None
    numeric_conflict: bool = False
    used_allowlist_fallback: bool = False


def _tokens(text: str) -> set[str]:
    return {t.lower() for t in _WORD.findall(text) if len(t) > 2}


def _capture_date(chunk: RetrievedChunk) -> str:
    return str(
        chunk.metadata.get("content_captured_at")
        or chunk.metadata.get("source_last_updated")
        or chunk.metadata.get("ingested_at")
        or ""
    )


def _allowed_urls() -> set[str]:
    return {s.source_url for s in load_sources_config().sources}


def _scheme_page_url(scheme_id: str | None) -> str | None:
    if not scheme_id:
        return None
    for s in load_sources_config().sources:
        if s.scheme_id == scheme_id:
            return s.source_url
    return None


def _url_allowed(url: str, allowed_domains: list[str]) -> bool:
    return any(domain in url for domain in allowed_domains)


def select_citation(
    chunks: list[RetrievedChunk],
    *,
    answer: str | None = None,
    scheme_id: str | None = None,
    allowed_domains: list[str] | None = None,
    numeric_conflict: bool = False,
) -> CitationResult:
    """Pick exactly one citation URL; primary rule = highest retrieval_score chunk."""
    if not chunks:
        return CitationResult(None, None, None)

    allowed_domains = allowed_domains or ["groww.in"]
    allowlist = _allowed_urls()

    if numeric_conflict:
        url = _scheme_page_url(scheme_id) or _scheme_page_url(
            str(chunks[0].metadata.get("scheme_id") or "") or None
        )
        if url and url in allowlist:
            return CitationResult(
                source_url=url,
                content_captured_at=_capture_date(chunks[0]),
                primary_chunk_id=chunks[0].chunk_id,
                numeric_conflict=True,
                used_allowlist_fallback=True,
            )

    ranked = sorted(chunks, key=lambda c: c.retrieval_score, reverse=True)
    primary = ranked[0]

    if answer:
        answer_tokens = _tokens(answer)
        best: RetrievedChunk | None = None
        best_score = -1.0
        for ch in ranked:
            overlap = len(answer_tokens & _tokens(ch.text))
            score = float(overlap) + ch.retrieval_score * 0.01
            if scheme_id and ch.metadata.get("scheme_id") == scheme_id:
                score += 2.0
            if score > best_score:
                best_score = score
                best = ch
            elif score == best_score and best:
                if _capture_date(ch) > _capture_date(best):
                    best = ch
        if best:
            primary = best

    for candidate in [primary, *ranked]:
        url = str(candidate.metadata.get("source_url", ""))
        if url in allowlist and _url_allowed(url, allowed_domains):
            return CitationResult(
                source_url=url,
                content_captured_at=_capture_date(candidate),
                primary_chunk_id=candidate.chunk_id,
                numeric_conflict=numeric_conflict,
            )

    fallback = _scheme_page_url(scheme_id)
    if fallback and fallback in allowlist:
        return CitationResult(
            source_url=fallback,
            content_captured_at=_capture_date(primary),
            primary_chunk_id=primary.chunk_id,
            used_allowlist_fallback=True,
        )

    return CitationResult(None, _capture_date(primary), primary.chunk_id)
