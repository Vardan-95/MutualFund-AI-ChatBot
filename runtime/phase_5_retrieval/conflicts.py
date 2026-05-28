from __future__ import annotations

import re

from runtime.phase_5_retrieval.models import RetrievedChunk

_METRIC_PATTERNS: dict[str, re.Pattern[str]] = {
    "expense_ratio": re.compile(
        r"expense\s+ratio[:\s]*(\d+(?:\.\d+)?)\s*%",
        re.I,
    ),
    "exit_load": re.compile(
        r"exit\s+load[:\s]*([^.\n]{0,80})",
        re.I,
    ),
}

_NUMERIC_CLAIM = re.compile(
    r"(\d+(?:\.\d+)?)\s*%|₹\s*[\d,]+(?:\.\d+)?",
)


def _is_compare_noise(chunk: RetrievedChunk) -> bool:
    t = chunk.text.lower()
    return "compare similar" in t or "/compare/" in t


def detect_numeric_conflict(chunks: list[RetrievedChunk]) -> bool:
    """True when top chunks disagree on the same labeled metric within one scheme."""
    seen: dict[tuple[str, str], set[str]] = {}
    for ch in chunks:
        if _is_compare_noise(ch):
            continue
        scheme = str(ch.metadata.get("scheme_id") or "")
        for label, pattern in _METRIC_PATTERNS.items():
            m = pattern.search(ch.text)
            if not m:
                continue
            val = m.group(1).strip().lower()
            key = (scheme, label)
            bucket = seen.setdefault(key, set())
            bucket.add(val)
            if len(bucket) > 1:
                return True
    return False


def chunks_contain_unsafe_numeric_spread(chunks: list[RetrievedChunk]) -> bool:
    """Disabled by default — compare tables on Groww pages trigger false positives."""
    return False
