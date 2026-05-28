"""Re-exports P2 intent router (use phases.p2_compliance for new code)."""

from phases.p2_compliance import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_FACTUAL,
    INTENT_OUT_OF_SCOPE,
    INTENT_PERFORMANCE,
    INTENT_PROCESS,
    IntentResult,
    classify_intent,
    detect_scheme_id,
)

__all__ = [
    "IntentResult",
    "classify_intent",
    "detect_scheme_id",
    "INTENT_FACTUAL",
    "INTENT_PROCESS",
    "INTENT_PERFORMANCE",
    "INTENT_ADVISORY",
    "INTENT_COMPARISON",
    "INTENT_OUT_OF_SCOPE",
]
