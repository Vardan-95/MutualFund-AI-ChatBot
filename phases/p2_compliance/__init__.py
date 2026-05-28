"""P2 — Intent routing, refusal, and output guardrails (RAG Architecture §3.3.1, §3.3.4)."""

from phases.p2_compliance.guardrails import GuardrailResult, apply_guardrails, run_guardrails
from phases.p2_compliance.intent_router import IntentResult, classify_intent
from phases.p2_compliance.intents import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_FACTUAL,
    INTENT_OUT_OF_SCOPE,
    INTENT_PERFORMANCE,
    INTENT_PROCESS,
    BLOCKED_INTENTS,
)
from phases.p2_compliance.scheme_scope import detect_scheme_id

__all__ = [
    "IntentResult",
    "GuardrailResult",
    "classify_intent",
    "apply_guardrails",
    "run_guardrails",
    "detect_scheme_id",
    "INTENT_FACTUAL",
    "INTENT_PROCESS",
    "INTENT_PERFORMANCE",
    "INTENT_ADVISORY",
    "INTENT_COMPARISON",
    "INTENT_OUT_OF_SCOPE",
    "BLOCKED_INTENTS",
]
