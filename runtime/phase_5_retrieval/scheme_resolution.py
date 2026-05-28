from __future__ import annotations

import re
from dataclasses import dataclass

from phases.common.config_loader import load_sources_config

_TICKER = re.compile(r"\b[A-Z]{2,6}\b")


@dataclass(frozen=True)
class SchemeResolution:
    scheme_id: str | None
    confidence: float
    amc_name: str | None
    matched_label: str | None = None


def resolve_scheme(query: str) -> SchemeResolution:
    """Dictionary match against in-scope schemes; returns confidence for metadata filter."""
    sources = load_sources_config()
    amc_name = sources.amc_name
    q_lower = query.lower()
    q_norm = re.sub(r"[-_/]+", " ", q_lower)
    best_len = 0
    best_id: str | None = None
    best_conf = 0.0
    best_label: str | None = None

    for s in sources.sources:
        candidates: list[tuple[str, float]] = [
            (s.scheme_name, 1.0),
            (s.scheme_id.replace("_", " "), 0.95),
            (
                s.source_url.rstrip("/").split("/")[-1].replace("-", " "),
                0.9,
            ),
        ]
        for label, conf in candidates:
            label_l = label.lower()
            label_norm = re.sub(r"[-_/]+", " ", label_l)
            if (label_l in q_lower or label_norm in q_norm) and len(label_norm) > best_len:
                best_len = len(label_norm)
                best_id = s.scheme_id
                best_conf = conf
                best_label = label

    if best_id:
        return SchemeResolution(
            scheme_id=best_id,
            confidence=best_conf,
            amc_name=amc_name,
            matched_label=best_label,
        )

    aliases: dict[str, tuple[str, float]] = {
        "mid cap": ("hdfc_mid_cap_direct_growth", 0.78),
        "large cap": ("hdfc_large_cap_direct_growth", 0.78),
        "elss": ("hdfc_elss_direct_growth", 0.8),
        "tax saver": ("hdfc_elss_direct_growth", 0.75),
        "focused": ("hdfc_focused_direct_growth", 0.75),
        "equity fund": ("hdfc_equity_direct_growth", 0.72),
    }
    for phrase, (sid, conf) in aliases.items():
        if phrase in q_lower or phrase in q_norm:
            return SchemeResolution(
                scheme_id=sid,
                confidence=conf,
                amc_name=amc_name,
                matched_label=phrase,
            )

    # HDFC mentioned without a specific scheme — AMC hint only
    if re.search(r"\bhdfc\b", query, re.I):
        return SchemeResolution(
            scheme_id=None,
            confidence=0.5,
            amc_name=amc_name,
            matched_label="hdfc",
        )

    return SchemeResolution(
        scheme_id=None,
        confidence=0.0,
        amc_name=None,
        matched_label=None,
    )


def preserve_entities(query: str) -> set[str]:
    """Tokens that should not be lowercased away during lexical matching."""
    entities: set[str] = set()
    for s in load_sources_config().sources:
        for part in re.findall(r"[A-Za-z0-9]+", s.scheme_name):
            if len(part) > 2:
                entities.add(part)
        entities.add(s.scheme_id)
    for m in _TICKER.findall(query):
        entities.add(m)
    return entities
