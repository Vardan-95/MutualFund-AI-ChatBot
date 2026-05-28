from __future__ import annotations

import re

_FOLLOWUP_HINTS = re.compile(
    r"\b(what about|how about|same scheme|that fund|it|this fund|exit load|expense ratio|minimum sip|nav)\b",
    re.I,
)


def expand_query_from_history(
    query: str,
    prior_user_lines: list[str],
) -> str:
    """§8.2 — rewrite using recent user lines only (no assistant echo, no PII expansion)."""
    q = query.strip()
    if not prior_user_lines or not _FOLLOWUP_HINTS.search(q):
        return q

    prev = prior_user_lines[-1].strip()
    if not prev or prev.lower() == q.lower():
        return q

    if len(q.split()) <= 8:
        return f"{prev}\nFollow-up: {q}"
    return q


def is_followup_query(query: str) -> bool:
    """Heuristic used to decide when prior turns should be injected."""
    return bool(_FOLLOWUP_HINTS.search(query.strip()))
