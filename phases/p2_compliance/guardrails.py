from __future__ import annotations

import re
from dataclasses import dataclass

from phases.common.config_loader import load_sources_config
from phases.p2_compliance.config import ComplianceConfig, load_compliance_config
from phases.p2_compliance.intents import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_OUT_OF_SCOPE,
    INTENT_PERFORMANCE,
)
from phases.p2_compliance.refusal import performance_guard_message, refusal_message
from pipeline.rag.answer_format import looks_like_table_dump, polish_answer

_URL_RE = re.compile(r"https?://[^\s\])>]+", re.I)
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
_PII_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PII_PHONE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_PII_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")


@dataclass
class GuardrailResult:
    text: str
    blocked: bool
    flags: list[str]


def apply_guardrails(
    answer: str,
    *,
    cfg: ComplianceConfig | None = None,
    education_url: str | None = None,
    citation_url: str | None = None,
    allowed_domains: list[str] | None = None,
    refused: bool = False,
    intent: str | None = None,
    context_text: str = "",
    max_sentences: int | None = None,
) -> str:
    return run_guardrails(
        answer,
        cfg=cfg,
        education_url=education_url,
        citation_url=citation_url,
        allowed_domains=allowed_domains,
        refused=refused,
        intent=intent,
        context_text=context_text,
        max_sentences=max_sentences,
    ).text


def run_guardrails(
    answer: str,
    *,
    cfg: ComplianceConfig | None = None,
    education_url: str | None = None,
    citation_url: str | None = None,
    allowed_domains: list[str] | None = None,
    refused: bool = False,
    intent: str | None = None,
    context_text: str = "",
    max_sentences: int | None = None,
) -> GuardrailResult:
    cfg = cfg or load_compliance_config()
    edu = education_url or cfg.education_url
    max_s = max_sentences if max_sentences is not None else cfg.max_sentences
    flags: list[str] = []

    if refused:
        return GuardrailResult(text=answer.strip(), blocked=True, flags=["refused"])

    text = answer.strip()
    if cfg.redact_pii:
        text, pii = _redact_pii(text)
        if pii:
            flags.append("pii_redacted")

    text = polish_answer(text, max_sentences=max_s)
    for phrase in cfg.forbidden_output_patterns:
        if phrase.lower() in text.lower():
            return GuardrailResult(
                text=refusal_message(INTENT_ADVISORY, edu),
                blocked=True,
                flags=flags + ["forbidden_phrase"],
            )

    if looks_like_table_dump(text):
        text = (
            "I could not format a concise factual answer. "
            "Please see the cited Groww scheme page for details."
        )
        flags.append("table_dump")

    text = _URL_RE.sub("", text).strip()
    text = re.sub(r"\s*Source:\s*", "", text, flags=re.I).strip()

    if _ADVISORY_OUTPUT.search(text):
        return GuardrailResult(
            text=refusal_message(INTENT_ADVISORY, edu),
            blocked=True,
            flags=flags + ["advisory_language"],
        )

    if _COMPARISON_OUTPUT.search(text):
        return GuardrailResult(
            text=refusal_message(INTENT_COMPARISON, edu),
            blocked=True,
            flags=flags + ["comparison_language"],
        )

    if cfg.block_performance_synthesis and intent == INTENT_PERFORMANCE:
        if _UNSANCTIONED_RETURN.search(text) and not _context_supports_numbers(text, context_text):
            url = citation_url or _default_source_url()
            text = performance_guard_message("this fund", url)
            flags.append("performance_synthesis")

    if citation_url:
        if allowed_domains and not _url_allowed(citation_url, allowed_domains):
            return GuardrailResult(
                text=refusal_message(INTENT_OUT_OF_SCOPE, edu),
                blocked=True,
                flags=flags + ["citation_domain"],
            )
        if citation_url not in _allowed_corpus_urls():
            return GuardrailResult(
                text=refusal_message(INTENT_OUT_OF_SCOPE, edu),
                blocked=True,
                flags=flags + ["citation_not_in_corpus"],
            )

    return GuardrailResult(text=text.strip(), blocked=False, flags=flags)


def _redact_pii(text: str) -> tuple[str, bool]:
    found = False
    for pattern in (_PII_EMAIL, _PII_PHONE, _PII_PAN):
        if pattern.search(text):
            found = True
            text = pattern.sub("[redacted]", text)
    return text, found


def _context_supports_numbers(answer: str, context: str) -> bool:
    for match in _UNSANCTIONED_RETURN.finditer(answer):
        if match.group(0).lower() in context.lower():
            return True
    return False


def _url_allowed(url: str, domains: list[str]) -> bool:
    return any(d in url for d in domains)


def _allowed_corpus_urls() -> set[str]:
    return {s.source_url for s in load_sources_config().sources}


def _default_source_url() -> str:
    sources = load_sources_config().sources
    return sources[0].source_url if sources else "https://groww.in"
