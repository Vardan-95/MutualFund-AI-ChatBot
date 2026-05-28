from __future__ import annotations

import re
from dataclasses import dataclass

from runtime.phase_5_retrieval.scheme_resolution import SchemeResolution, resolve_scheme

_VOCAB: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\bter\b", re.I), "expense ratio"),
    (re.compile(r"\bexit fee\b", re.I), "exit load"),
]

_WORD = re.compile(r"[a-z0-9]+", re.I)


@dataclass(frozen=True)
class PreprocessedQuery:
    original: str
    dense_query: str
    match_query: str
    scheme: SchemeResolution
    apply_scheme_filter: bool


def preprocess_query(
    query: str,
    *,
    scheme_filter_min_confidence: float = 0.85,
    scheme: SchemeResolution | None = None,
) -> PreprocessedQuery:
    original = query.strip()
    expanded = original
    for pattern, replacement in _VOCAB:
        expanded = pattern.sub(replacement, expanded)

    scheme = scheme or resolve_scheme(expanded)
    apply_filter = (
        scheme.scheme_id is not None
        and scheme.confidence >= scheme_filter_min_confidence
    )

    match_query = expanded.lower()
    dense_query = expanded

    return PreprocessedQuery(
        original=original,
        dense_query=dense_query,
        match_query=match_query,
        scheme=scheme,
        apply_scheme_filter=apply_filter,
    )


def query_terms_for_match(preprocessed: PreprocessedQuery) -> set[str]:
    return {t.lower() for t in _WORD.findall(preprocessed.match_query) if len(t) > 1}
