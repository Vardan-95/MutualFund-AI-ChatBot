from __future__ import annotations

import re

from pipeline.rag.models import RetrievedChunk

_TABLE_ROW = re.compile(r"^\s*\|(.+)\|\s*$", re.M)
_TABLE_SEP = re.compile(r"^\s*\|[\s\-:|]+\|\s*$", re.M)
_MARKDOWN_HEADING = re.compile(r"^#{1,6}\s+", re.M)
_URL_RE = re.compile(r"https?://\S+", re.I)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# Query term → row label in metrics table
_METRIC_ALIASES: dict[str, tuple[str, ...]] = {
    "expense ratio": ("expense ratio", "ter"),
    "minimum sip": ("minimum sip", "min sip"),
    "min sip": ("minimum sip", "min sip"),
    "sip": ("minimum sip",),
    "nav": ("nav",),
    "aum": ("fund size", "aum"),
    "fund size": ("fund size", "aum"),
    "rating": ("rating",),
    "exit load": ("exit load",),
    "lock-in": ("lock-in", "lock in"),
    "lock in": ("lock-in", "lock in"),
}


def simplify_context_for_llm(text: str) -> str:
    """Turn markdown tables into plain facts so the model is less likely to copy pipes."""
    if "|" not in text or "metric" not in text.lower():
        return text
    facts = parse_metrics_table(text)
    if facts:
        return "Facts from scheme page: " + "; ".join(f"{k}: {v}" for k, v in facts.items())
    return text


def parse_metrics_table(text: str) -> dict[str, str]:
    facts: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line.startswith("|") or _TABLE_SEP.match(line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        label, value = cells[0], cells[1]
        if label.lower() in ("metric", "value", ""):
            continue
        facts[label] = value
    return facts


def looks_like_table_dump(text: str) -> bool:
    if not text or "|" not in text:
        return False
    if text.count("|") >= 4:
        return True
    if "---" in text and "|" in text:
        return True
    if re.search(r"metric\s*\|\s*value", text, re.I):
        return True
    return False


def polish_answer(text: str, *, max_sentences: int = 3) -> str:
    """Strip tables/markdown noise and enforce sentence limit."""
    text = (text or "").strip()
    text = _URL_RE.sub("", text)
    text = _MARKDOWN_HEADING.sub("", text)
    text = _strip_table_lines(text)
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"^Source:\s*", "", text, flags=re.I).strip()

    if looks_like_table_dump(text) or not text:
        return ""

    sentences = _split_sentences(text)
    if not sentences:
        return text[:400]
    return " ".join(sentences[:max_sentences])


def _strip_table_lines(text: str) -> str:
    lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if _TABLE_SEP.match(stripped):
            continue
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if len(cells) >= 2 and cells[0].lower() not in ("metric", "value"):
                lines.append(f"{cells[0]} is {cells[1]}.")
            continue
        if stripped:
            lines.append(stripped)
    return " ".join(lines)


def _split_sentences(text: str) -> list[str]:
    parts = [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]
    cleaned: list[str] = []
    for s in parts:
        s = re.sub(r"^[\-\*•]\s*", "", s)
        if s and not looks_like_table_dump(s):
            cleaned.append(s)
    return cleaned


def structured_answer_from_chunks(
    query: str,
    chunks: list[RetrievedChunk],
) -> str | None:
    """Build ≤3 plain sentences from metrics tables when the LLM dumps markdown."""
    q = query.lower()
    best = _pick_metrics_chunk(chunks)
    if not best:
        return None

    facts = parse_metrics_table(best.text)
    if not facts:
        return None

    scheme = str(best.metadata.get("scheme_name", "This fund"))
    matched = _match_metric_keys(q, facts)
    if matched:
        parts: list[str] = []
        seen: set[str] = set()
        for label, value in matched:
            key = label.lower()
            if key in seen:
                continue
            seen.add(key)
            parts.append(f"The {label} for {scheme} is {value}.")
            if len(parts) >= 3:
                break
        return " ".join(parts)

    # Generic: top 2–3 metrics
    items = list(facts.items())[:3]
    return " ".join(f"The {k} for {scheme} is {v}." for k, v in items)


def _pick_metrics_chunk(chunks: list[RetrievedChunk]) -> RetrievedChunk | None:
    for ch in chunks:
        if ch.metadata.get("section_canonical") == "key_fund_metrics":
            if parse_metrics_table(ch.text):
                return ch
    for ch in chunks:
        if parse_metrics_table(ch.text):
            return ch
    return chunks[0] if chunks else None


def _match_metric_keys(
    query: str,
    facts: dict[str, str],
) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    seen_labels: set[str] = set()
    fact_lower = {k.lower(): (k, v) for k, v in facts.items()}
    for _phrase, aliases in _METRIC_ALIASES.items():
        if not any(a in query for a in aliases):
            continue
        for key, (label, value) in fact_lower.items():
            if any(a in key for a in aliases) and label.lower() not in seen_labels:
                seen_labels.add(label.lower())
                results.append((label, value))
                break
    return results
