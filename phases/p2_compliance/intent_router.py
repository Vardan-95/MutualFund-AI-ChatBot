from __future__ import annotations

import re
from dataclasses import dataclass

from phases.p2_compliance.config import ComplianceConfig, load_compliance_config
from phases.p2_compliance.embedding_classifier import classify_by_exemplars
from phases.p2_compliance.intents import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_FACTUAL,
    INTENT_OUT_OF_SCOPE,
    INTENT_PERFORMANCE,
    INTENT_PROCESS,
)
from phases.p2_compliance.refusal import refusal_message
from phases.p2_compliance.scheme_scope import detect_scheme_id, is_in_scope_scheme

_COMPILED: dict[str, list[re.Pattern[str]]] = {}
_FACTUAL_METRIC_HINT = re.compile(
    r"\b(nav|expense ratio|ter|exit load|min(imum)? sip|\bsip\b|aum|fund size|"
    r"benchmark|riskometer|rating|lock[- ]?in|launch date|holding|holdings|"
    r"weight|allocation|portfolio|top holdings|sector exposure)\b",
    re.I,
)


@dataclass(frozen=True)
class IntentResult:
    intent: str
    scheme_id: str | None
    refusal: bool
    refusal_message: str | None = None
    education_url: str | None = None
    matched_by: str = "default"  # rule | embedding | scope


def _patterns(cfg: ComplianceConfig, key: str, raw: list[str]) -> list[re.Pattern[str]]:
    if key not in _COMPILED:
        _COMPILED[key] = [re.compile(p, re.I) for p in raw]
    return _COMPILED[key]


def _any_match(query: str, patterns: list[re.Pattern[str]]) -> bool:
    return any(p.search(query) for p in patterns)


def _looks_like_factual_metric_query(query: str) -> bool:
    return bool(_FACTUAL_METRIC_HINT.search(query))


def classify_intent(
    query: str,
    education_url: str | None = None,
    *,
    cfg: ComplianceConfig | None = None,
) -> IntentResult:
    cfg = cfg or load_compliance_config()
    edu = education_url or cfg.education_url
    q = query.strip()
    scheme_id = detect_scheme_id(q)

    # Hard blocks — no retrieval
    if _any_match(q, _patterns(cfg, "advisory", cfg.advisory_patterns)):
        return IntentResult(
            intent=INTENT_ADVISORY,
            scheme_id=scheme_id,
            refusal=True,
            refusal_message=refusal_message(INTENT_ADVISORY, edu),
            education_url=edu,
            matched_by="rule",
        )

    if _any_match(q, _patterns(cfg, "comparison", cfg.comparison_patterns)):
        return IntentResult(
            intent=INTENT_COMPARISON,
            scheme_id=scheme_id,
            refusal=True,
            refusal_message=refusal_message(INTENT_COMPARISON, edu),
            education_url=edu,
            matched_by="rule",
        )

    # Embedding exemplars (edge-case advisory/comparison).
    # Skip exemplar matching for direct metric lookups to avoid
    # false advisory routing on plain factual questions.
    emb_label, _score = (None, 0.0)
    if not _looks_like_factual_metric_query(q):
        emb_label, _score = classify_by_exemplars(q, cfg)
    if emb_label == INTENT_ADVISORY:
        return IntentResult(
            intent=INTENT_ADVISORY,
            scheme_id=scheme_id,
            refusal=True,
            refusal_message=refusal_message(INTENT_ADVISORY, edu),
            education_url=edu,
            matched_by="embedding",
        )
    if emb_label == INTENT_COMPARISON:
        return IntentResult(
            intent=INTENT_COMPARISON,
            scheme_id=scheme_id,
            refusal=True,
            refusal_message=refusal_message(INTENT_COMPARISON, edu),
            education_url=edu,
            matched_by="embedding",
        )

    # Other AMC / fund houses
    q_lower = q.lower()
    if any(kw in q_lower for kw in cfg.out_of_scope_amc_keywords):
        if not re.search(r"\bhdfc\b", q, re.I) and scheme_id is None:
            return IntentResult(
                intent=INTENT_OUT_OF_SCOPE,
                scheme_id=None,
                refusal=True,
                refusal_message=refusal_message(INTENT_OUT_OF_SCOPE, edu),
                education_url=edu,
                matched_by="scope",
            )

    # Unknown scheme mention with fund keywords but not in allowlist
    if scheme_id and not is_in_scope_scheme(scheme_id):
        return IntentResult(
            intent=INTENT_OUT_OF_SCOPE,
            scheme_id=None,
            refusal=True,
            refusal_message=refusal_message(INTENT_OUT_OF_SCOPE, edu, scheme_hint=True),
            education_url=edu,
            matched_by="scope",
        )

    if scheme_id is None and re.search(r"\bhdfc\b", q, re.I) is None:
        if re.search(r"\bmutual fund\b", q, re.I) and re.search(
            r"\b(fund|scheme|nav|sip)\b", q, re.I
        ):
            return IntentResult(
                intent=INTENT_OUT_OF_SCOPE,
                scheme_id=None,
                refusal=True,
                refusal_message=refusal_message(INTENT_OUT_OF_SCOPE, edu, scheme_hint=True),
                education_url=edu,
                matched_by="scope",
            )

    if _any_match(q, _patterns(cfg, "performance", cfg.performance_patterns)):
        return IntentResult(
            intent=INTENT_PERFORMANCE,
            scheme_id=scheme_id,
            refusal=False,
            education_url=edu,
            matched_by="rule",
        )

    if _any_match(q, _patterns(cfg, "process", cfg.process_patterns)):
        return IntentResult(
            intent=INTENT_PROCESS,
            scheme_id=scheme_id,
            refusal=False,
            education_url=edu,
            matched_by="rule",
        )

    return IntentResult(
        intent=INTENT_FACTUAL,
        scheme_id=scheme_id,
        refusal=False,
        education_url=edu,
        matched_by="default",
    )
