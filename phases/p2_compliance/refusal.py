from __future__ import annotations

from phases.p2_compliance.intents import (
    INTENT_ADVISORY,
    INTENT_COMPARISON,
    INTENT_OUT_OF_SCOPE,
)


def refusal_message(intent: str, education_url: str, *, scheme_hint: bool = False) -> str:
    if intent == INTENT_ADVISORY:
        return (
            "I'm a facts-only assistant and can't provide investment advice or recommendations. "
            f"For general investor education, see: {education_url}"
        )
    if intent == INTENT_COMPARISON:
        return (
            "I can't compare funds or say which is better—that would be investment advice. "
            "I can share factual details about one HDFC scheme at a time from Groww. "
            f"For general investor education, see: {education_url}"
        )
    if intent == INTENT_OUT_OF_SCOPE:
        scope = (
            "I only cover five HDFC schemes on Groww: Mid Cap, Equity, Focused, ELSS, and Large Cap (Direct Growth). "
        )
        if scheme_hint:
            return scope + "Please name one of those funds."
        return scope + "Ask about a specific scheme or fact from those pages."
    return (
        "I'm a facts-only assistant and can't provide investment advice or recommendations. "
        f"For general investor education, see: {education_url}"
    )


def performance_guard_message(scheme_name: str, source_url: str) -> str:
    return (
        f"I don't calculate, rank, or compare returns. "
        f"For published figures, see the Groww page for {scheme_name}: {source_url}"
    )
