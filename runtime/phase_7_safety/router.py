from __future__ import annotations

import re
from dataclasses import dataclass

from phases.p2_compliance.config import ComplianceConfig
from phases.p2_compliance.intent_router import IntentResult, classify_intent

_PERSONAL_SITUATION = re.compile(
    r"\b(i am|i'm|im)\s+\d{2,3}\b|\b(age|aged)\s+\d{2,3}\b",
    re.I,
)


@dataclass(frozen=True)
class RouteResult:
    intent: IntentResult
    blocked_before_retrieval: bool


def route_query(
    query: str,
    education_url: str | None = None,
    *,
    cfg: ComplianceConfig | None = None,
) -> RouteResult:
    """§7.1 — rules + embedding classifier; no retrieval when refused."""
    from runtime.phase_7_safety.config import load_safety_config

    compliance, rag = load_safety_config()
    compliance = cfg or compliance
    edu = education_url or rag.refusal_education_url
    intent = classify_intent(query, edu, cfg=compliance)

    if not intent.refusal and _PERSONAL_SITUATION.search(query):
        from phases.p2_compliance.intents import INTENT_ADVISORY
        from phases.p2_compliance.refusal import refusal_message

        intent = IntentResult(
            intent=INTENT_ADVISORY,
            scheme_id=intent.scheme_id,
            refusal=True,
            refusal_message=refusal_message(INTENT_ADVISORY, edu),
            education_url=edu,
            matched_by="rule_personal",
        )

    return RouteResult(
        intent=intent,
        blocked_before_retrieval=bool(intent.refusal),
    )
