from __future__ import annotations

import re
from dataclasses import dataclass

from phases.p2_compliance.config import ComplianceConfig
from phases.p2_compliance.intents import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_OUT_OF_SCOPE,
    INTENT_PERFORMANCE,
)
from phases.p2_compliance.refusal import performance_guard_message, refusal_message
from phases.common.config_loader import load_sources_config
from pipeline.rag.answer_format import looks_like_table_dump, polish_answer
from runtime.phase_7_safety.pii import redact_pii

_URL_RE = re.compile(r"https?://[^\s\])>]+", re.I)
_SENTENCE_END = re.compile(r"[.!?]+")

_ADVISORY_OUTPUT = re.compile(
    r"\b(you should invest|i recommend|buy this fund|sell this fund|best choice|"
    r"better fund|outperformed|which is better)\b",
    re.I,
)
_COMPARISON_OUTPUT = re.compile(
    r"\b(compare|versus| vs |better than|higher returns than)\b",
    re.I,
)
_UNSANCTIONED_RETURN = re.compile(
    r"\b(\d+(\.\d+)?%|cagr|x return|times return)\b",
    re.I,
)


@dataclass
class ValidationResult:
    text: str
    ok: bool
    blocked: bool
    should_retry: bool
    flags: list[str]


def count_sentences(text: str) -> int:
    text = text.strip()
    if not text:
        return 0
    parts = [p for p in _SENTENCE_END.split(text) if p.strip()]
    return max(1, len(parts))


def validate_output(
    answer: str,
    *,
    cfg: ComplianceConfig,
    education_url: str,
    citation_url: str | None,
    allowed_domains: list[str],
    intent: str | None,
    context_text: str = "",
    max_sentences: int | None = None,
) -> ValidationResult:
    """§7.2 — programmatic checks after generation."""
    max_s = max_sentences if max_sentences is not None else cfg.max_sentences
    flags: list[str] = []
    text = answer.strip()

    if cfg.redact_pii:
        text, pii = redact_pii(text)
        if pii:
            flags.append("pii_redacted")

    urls_in_body = _URL_RE.findall(text)
    if len(urls_in_body) > 1:
        flags.append("multiple_urls")
        return ValidationResult(
            text=text,
            ok=False,
            blocked=False,
            should_retry=True,
            flags=flags,
        )

    text = _URL_RE.sub("", text).strip()
    text = re.sub(r"\s*Source:\s*", "", text, flags=re.I).strip()
    text = polish_answer(text, max_sentences=max_s)

    if not text or looks_like_table_dump(text):
        return ValidationResult(
            text=text,
            ok=False,
            blocked=False,
            should_retry=True,
            flags=flags + ["table_dump"],
        )

    if count_sentences(text) > max_s:
        flags.append("sentence_limit")
        text = polish_answer(text, max_sentences=max_s)

    for phrase in cfg.forbidden_output_patterns:
        if phrase.lower() in text.lower():
            flags.append("forbidden_phrase")
            return ValidationResult(
                text=text,
                ok=False,
                blocked=False,
                should_retry=True,
                flags=flags,
            )

    if _ADVISORY_OUTPUT.search(text):
        return ValidationResult(
            text=refusal_message(INTENT_ADVISORY, education_url),
            ok=False,
            blocked=True,
            should_retry=False,
            flags=flags + ["advisory_language"],
        )

    if _COMPARISON_OUTPUT.search(text):
        return ValidationResult(
            text=refusal_message(INTENT_COMPARISON, education_url),
            ok=False,
            blocked=True,
            should_retry=False,
            flags=flags + ["comparison_language"],
        )

    if cfg.block_performance_synthesis and intent == INTENT_PERFORMANCE:
        if _UNSANCTIONED_RETURN.search(text) and not _context_supports_numbers(
            text, context_text
        ):
            url = citation_url or _default_source_url()
            return ValidationResult(
                text=performance_guard_message("this fund", url),
                ok=True,
                blocked=False,
                should_retry=False,
                flags=flags + ["performance_synthesis"],
            )

    if citation_url:
        if allowed_domains and not any(d in citation_url for d in allowed_domains):
            return ValidationResult(
                text=refusal_message(INTENT_OUT_OF_SCOPE, education_url),
                ok=False,
                blocked=True,
                should_retry=False,
                flags=flags + ["citation_domain"],
            )
        if citation_url not in _allowed_corpus_urls():
            return ValidationResult(
                text=refusal_message(INTENT_OUT_OF_SCOPE, education_url),
                ok=False,
                blocked=True,
                should_retry=False,
                flags=flags + ["citation_not_in_corpus"],
            )

    return ValidationResult(
        text=text.strip(),
        ok=True,
        blocked=False,
        should_retry=False,
        flags=flags,
    )


def _context_supports_numbers(answer: str, context: str) -> bool:
    for match in _UNSANCTIONED_RETURN.finditer(answer):
        if match.group(0).lower() in context.lower():
            return True
    return False


def _allowed_corpus_urls() -> set[str]:
    return {s.source_url for s in load_sources_config().sources}


def _default_source_url() -> str:
    sources = load_sources_config().sources
    return sources[0].source_url if sources else "https://groww.in"
