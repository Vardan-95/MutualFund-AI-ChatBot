from __future__ import annotations

import json
from functools import lru_cache

from phases.common.config_loader import load_sources_config
from phases.p2_compliance.intents import INTENT_PERFORMANCE
from pipeline.rag.models import RAGResponse
from runtime.phase_5_retrieval.citation import select_citation
from runtime.phase_5_retrieval.performance import performance_link_only_answer
from runtime.phase_5_retrieval.retriever import HybridRetriever
from runtime.phase_6_generation.config import load_generation_config
from runtime.phase_6_generation.context import format_footer
from runtime.phase_6_generation.generator import generate_body, templated_safe_fallback
from runtime.phase_7_safety.config import load_safety_config
from runtime.phase_7_safety.router import route_query
from runtime.phase_7_safety.validation import validate_output

_retriever: HybridRetriever | None = None


def _get_retriever() -> HybridRetriever:
    global _retriever
    if _retriever is None:
        _retriever = HybridRetriever()
    return _retriever


def warmup_rag_stack() -> None:
    """Load BM25, Chroma client, and local embedding model before first user message."""
    retriever = _get_retriever()
    retriever._embedder.embed_batch(["warmup query"])


@lru_cache(maxsize=1)
def _corpus_version(manifest_path: str) -> int | None:
    from pathlib import Path

    path = Path(manifest_path)
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    return int(data.get("corpus_version", 0)) or None


def _scheme_name(scheme_id: str | None) -> str:
    if not scheme_id:
        return "this fund"
    for s in load_sources_config().sources:
        if s.scheme_id == scheme_id:
            return s.scheme_name
    return "this fund"


def _list_supported_schemes(query: str) -> str | None:
    q = query.lower()
    if "hdfc" not in q:
        return None
    if not any(
        phrase in q
        for phrase in (
            "5 scheme",
            "five scheme",
            "which schemes",
            "what schemes",
            "list schemes",
            "supported schemes",
        )
    ):
        return None
    names = [s.scheme_name for s in load_sources_config().sources]
    if not names:
        return None
    return (
        "I cover these five HDFC schemes on Groww: "
        + ", ".join(names)
        + "."
    )


def answer(
    query: str,
    *,
    thread_context: str | None = None,
) -> RAGResponse:
    """Orchestrate §7 route → §5 retrieve → §6 generate → §7.2 validate."""
    compliance, rag = load_safety_config()
    gen_cfg = load_generation_config()
    full_query = query.strip()
    if thread_context:
        full_query = f"{thread_context.strip()}\n{full_query}"

    scheme_list_reply = _list_supported_schemes(full_query)
    if scheme_list_reply:
        return RAGResponse(
            answer=scheme_list_reply,
            intent="PROCESS_HOWTO",
            source_url=None,
            content_captured_at=None,
            corpus_version=_corpus_version(str(rag.manifest_path)),
            refused=False,
            disclaimer=rag.disclaimer,
            intent_matched_by="rule_scope_list",
        )

    routed = route_query(full_query, cfg=compliance)
    intent_result = routed.intent
    version = _corpus_version(str(rag.manifest_path))

    if routed.blocked_before_retrieval:
        return RAGResponse(
            answer=intent_result.refusal_message or "",
            intent=intent_result.intent,
            source_url=None,
            content_captured_at=None,
            corpus_version=version,
            refused=True,
            disclaimer=rag.disclaimer,
            education_url=intent_result.education_url,
            intent_matched_by=intent_result.matched_by,
        )

    retrieval = _get_retriever().retrieve(
        full_query,
        scheme_id=intent_result.scheme_id,
    )
    chunks = retrieval.chunks
    guard_flags: list[str] = []
    if retrieval.numeric_conflict:
        guard_flags.append("numeric_conflict")

    if not chunks:
        return RAGResponse(
            answer=(
                "I could not find relevant facts in the corpus for that question. "
                "Try naming one of the five HDFC schemes on Groww (mid cap, equity, focused, ELSS, large cap)."
            ),
            intent=intent_result.intent,
            source_url=None,
            content_captured_at=None,
            corpus_version=version,
            refused=False,
            disclaimer=rag.disclaimer,
            intent_matched_by=intent_result.matched_by,
        )

    if intent_result.intent == INTENT_PERFORMANCE:
        draft, url, captured = performance_link_only_answer(
            chunks,
            scheme_id=intent_result.scheme_id,
            allowed_domains=rag.allowed_citation_domains,
        )
        validated = validate_output(
            draft,
            cfg=compliance,
            education_url=rag.refusal_education_url,
            citation_url=url,
            allowed_domains=rag.allowed_citation_domains,
            intent=intent_result.intent,
            max_sentences=rag.max_sentences,
        )
        final = validated.text
        if captured and not validated.blocked:
            final = f"{final}\n\n{format_footer(captured)}"
        return RAGResponse(
            answer=final,
            intent=intent_result.intent,
            source_url=url if not validated.blocked else None,
            content_captured_at=captured,
            corpus_version=version,
            chunk_ids=[c.chunk_id for c in chunks],
            refused=validated.blocked,
            disclaimer=rag.disclaimer,
            education_url=intent_result.education_url if validated.blocked else None,
            intent_matched_by=intent_result.matched_by,
            guardrail_flags=guard_flags + validated.flags,
        )

    context_text = "\n".join(c.text for c in chunks)

    if retrieval.numeric_conflict:
        cite_scheme = intent_result.scheme_id or str(
            chunks[0].metadata.get("scheme_id") or ""
        )
        scheme_name = _scheme_name(cite_scheme or None)
        cite = select_citation(
            chunks,
            scheme_id=intent_result.scheme_id,
            allowed_domains=rag.allowed_citation_domains,
            numeric_conflict=True,
        )
        url = cite.source_url
        captured = cite.content_captured_at
        draft = (
            f"I cannot reconcile conflicting figures in my sources for {scheme_name}. "
            "Please verify on the Groww scheme page before acting."
        )
    else:
        gen = generate_body(full_query, chunks, cfg=gen_cfg)
        draft = gen.body
        cite = select_citation(
            chunks,
            answer=draft,
            scheme_id=intent_result.scheme_id,
            allowed_domains=rag.allowed_citation_domains,
        )
        url = cite.source_url
        captured = cite.content_captured_at

        validated = validate_output(
            draft,
            cfg=compliance,
            education_url=rag.refusal_education_url,
            citation_url=url,
            allowed_domains=rag.allowed_citation_domains,
            intent=intent_result.intent,
            context_text=context_text,
            max_sentences=rag.max_sentences,
        )
        draft = validated.text
        guard_flags.extend(validated.flags)

        if validated.should_retry and not validated.blocked:
            gen_retry = generate_body(full_query, chunks, cfg=gen_cfg, strict=True)
            validated2 = validate_output(
                gen_retry.body,
                cfg=compliance,
                education_url=rag.refusal_education_url,
                citation_url=url,
                allowed_domains=rag.allowed_citation_domains,
                intent=intent_result.intent,
                context_text=context_text,
                max_sentences=rag.max_sentences,
            )
            guard_flags.append("validation_retry")
            if validated2.ok and not validated2.should_retry:
                draft = validated2.text
                guard_flags.extend(validated2.flags)
            elif url:
                draft = templated_safe_fallback(_scheme_name(intent_result.scheme_id), url)
                guard_flags.append("templated_fallback")
            else:
                guard_flags.extend(validated2.flags)

    final_validation = validate_output(
        draft,
        cfg=compliance,
        education_url=rag.refusal_education_url,
        citation_url=url,
        allowed_domains=rag.allowed_citation_domains,
        intent=intent_result.intent,
        context_text=context_text,
        max_sentences=rag.max_sentences,
    )
    final = final_validation.text
    guard_flags.extend(final_validation.flags)

    if captured and not final_validation.blocked:
        final = f"{final}\n\n{format_footer(captured)}"

    return RAGResponse(
        answer=final,
        intent=intent_result.intent,
        source_url=url if not final_validation.blocked else None,
        content_captured_at=captured,
        corpus_version=version,
        chunk_ids=[c.chunk_id for c in chunks],
        refused=final_validation.blocked,
        disclaimer=rag.disclaimer,
        education_url=intent_result.education_url if final_validation.blocked else None,
        intent_matched_by=intent_result.matched_by,
        guardrail_flags=guard_flags,
    )
