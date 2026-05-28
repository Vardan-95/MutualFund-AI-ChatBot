from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass

from pipeline.config import ChunkingConfig
from pipeline.corpus_loader import CorpusDocument

_HEADING_MAP = {
    "key fund metrics": "key_fund_metrics",
    "fund overview": "fund_overview",
    "investment limits": "investment_limits",
    "fees and loads": "fees_and_loads",
    "risk and benchmark": "risk_and_benchmark",
    "returns and nav": "returns_and_nav",
    "fund details": "fund_details",
    "holdings and portfolio": "holdings_and_portfolio",
    "holdings": "holdings_and_portfolio",
    "tax and lock-in": "tax_and_lock_in",
    "exit load": "fees_and_loads",
}

_BOILERPLATE = [
    re.compile(r"^Invest in Stocks", re.I),
    re.compile(r"^Mutual Fund Houses", re.I),
    re.compile(r"^if \(Promise", re.I),
    re.compile(r"^function\s*\(", re.I),
]


@dataclass
class NormalizedDocument:
    document: CorpusDocument
    body: str
    content_hash: str


def normalize_document(doc: CorpusDocument, _cfg: ChunkingConfig) -> NormalizedDocument:
    body = doc.body
    body = unicodedata.normalize("NFC", body.replace("\r\n", "\n"))
    body = _keep_metrics_and_headings(body)
    lines: list[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if any(p.search(stripped) for p in _BOILERPLATE):
            continue
        if re.search(r"\b(Promise|document\.|window\.|globalThis|function\s*\()\b", stripped):
            continue
        if len(stripped) > 400:
            continue
        lines.append(line.rstrip())
    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body).strip()
    body = _repair_headings(body)
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    return NormalizedDocument(document=doc, body=body, content_hash=content_hash)


def _keep_metrics_and_headings(body: str) -> str:
    """Preserve Key fund metrics table and markdown headings; drop Groww JS chrome."""
    parts: list[str] = []
    metrics = re.search(
        r"(## Key fund metrics\s*\n(?:\|[^\n]+\n)+)",
        body,
        re.IGNORECASE,
    )
    if metrics:
        parts.append(metrics.group(1).strip())
        remainder = body[metrics.end() :]
    else:
        remainder = body

    for line in remainder.splitlines():
        stripped = line.strip()
        if re.match(r"^#{1,3}\s+\S", stripped):
            parts.append(stripped if stripped.startswith("##") else f"## {stripped.lstrip('#').strip()}")
        elif stripped.startswith("|") and parts and "Key fund metrics" not in parts[-1]:
            parts.append(stripped)
    return "\n\n".join(parts)


def _repair_headings(body: str) -> str:
    """Ensure ## headings use canonical section names where possible."""
    out_lines: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^##\s+(.+)$", line.strip())
        if m:
            title = m.group(1).strip().lower()
            canonical = _HEADING_MAP.get(title, title.replace(" ", "_"))
            display = canonical.replace("_", " ").title()
            if canonical == "key_fund_metrics":
                display = "Key fund metrics"
            out_lines.append(f"## {display}")
        else:
            out_lines.append(line)
    return "\n".join(out_lines)
