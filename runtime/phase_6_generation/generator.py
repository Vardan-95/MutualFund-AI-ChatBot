from __future__ import annotations

import re
from dataclasses import dataclass

from pipeline.rag.answer_format import (
    looks_like_table_dump,
    parse_metrics_table,
    polish_answer,
    structured_answer_from_chunks,
)
from runtime.phase_5_retrieval.models import RetrievedChunk
from runtime.phase_6_generation.config import GenerationConfig, load_generation_config
from runtime.phase_6_generation.llm import chat_completion, resolve_client


@dataclass
class GenerationResult:
    body: str
    used_llm: bool = False
    retried: bool = False
    fallback_used: bool = False


def generate_body(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    cfg: GenerationConfig | None = None,
    strict: bool = False,
) -> GenerationResult:
    cfg = cfg or load_generation_config()
    if not chunks:
        return GenerationResult(
            body=(
                "I cannot find that in the indexed Groww sources for the five HDFC schemes in scope."
            ),
            fallback_used=True,
        )

    # Deterministic path for metric-style questions (NAV, SIP, expense ratio, etc.).
    # This prevents compliant-but-empty LLM responses when the metric is present in tables.
    structured = structured_answer_from_chunks(query, chunks)
    if structured and _is_metric_query(query):
        return GenerationResult(
            body=polish_answer(structured, max_sentences=cfg.max_sentences),
            fallback_used=True,
        )

    client_info = resolve_client(cfg)
    if client_info:
        client, model, provider = client_info
        try:
            raw = chat_completion(client, model, query, chunks, cfg, strict=strict)
            polished = polish_answer(raw, max_sentences=cfg.max_sentences)
            if polished and not looks_like_table_dump(polished):
                return GenerationResult(body=polished, used_llm=True, retried=strict)

            if not strict:
                raw2 = chat_completion(client, model, query, chunks, cfg, strict=True)
                polished2 = polish_answer(raw2, max_sentences=cfg.max_sentences)
                if polished2 and not looks_like_table_dump(polished2):
                    return GenerationResult(
                        body=polished2,
                        used_llm=True,
                        retried=True,
                    )
        except Exception as exc:
            print(f"{provider} generation failed ({exc}); using structured fallback.")

    if structured:
        return GenerationResult(
            body=polish_answer(structured, max_sentences=cfg.max_sentences),
            fallback_used=True,
        )

    return GenerationResult(
        body=_extractive_fallback(chunks, cfg, query),
        fallback_used=True,
    )


def templated_safe_fallback(scheme_name: str, source_url: str) -> str:
    return (
        f"I could not produce a safe concise answer from the indexed sources for {scheme_name}. "
        f"Please see the Groww scheme page for verified facts."
    )


def _is_metric_query(query: str) -> bool:
    q = query.lower()
    terms = (
        "nav",
        "minimum sip",
        "sip",
        "expense ratio",
        "ter",
        "exit load",
        "aum",
        "fund size",
        "rating",
        "lock-in",
        "lock in",
    )
    return any(term in q for term in terms)


def _extractive_fallback(
    chunks: list[RetrievedChunk],
    cfg: GenerationConfig,
    query: str,
) -> str:
    best = chunks[0]
    for ch in chunks:
        if ch.metadata.get("section_canonical") == "key_fund_metrics":
            if parse_metrics_table(ch.text):
                best = ch
                break
    text = re.sub(r"\s+", " ", best.text.replace("\n", " ")).strip()
    if looks_like_table_dump(text):
        return (
            "I cannot find a clear factual sentence for that in the indexed sources. "
            "Try naming the HDFC scheme (mid cap, large cap, ELSS, equity, or focused)."
        )
    sentences = re.split(r"(?<=[.!?])\s+", text)
    sentences = [s for s in sentences if s and len(s) < 300][: cfg.max_sentences]
    if sentences:
        return " ".join(sentences)
    return text[:400]
