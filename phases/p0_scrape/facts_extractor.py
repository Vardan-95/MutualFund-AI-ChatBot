from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any

from bs4 import BeautifulSoup

# Groww label → internal field name
_LABEL_MAP = {
    "Expense ratio": "expense_ratio",
    "Min. for SIP": "minimum_sip",
    "Fund size (AUM)": "fund_size_aum",
    "Rating": "rating",
}


@dataclass
class FundFacts:
    scheme_id: str
    scheme_name: str
    source_url: str
    content_captured_at: str
    scrape_run_id: str
    nav: dict[str, Any] | None = None
    minimum_sip: dict[str, Any] | None = None
    fund_size_aum: dict[str, Any] | None = None
    expense_ratio: dict[str, Any] | None = None
    rating: dict[str, Any] | None = None
    extraction_status: str = "partial"
    missing_fields: list[str] = field(default_factory=list)

    def facts_hash(self) -> str:
        payload = {
            "nav": self.nav,
            "minimum_sip": self.minimum_sip,
            "fund_size_aum": self.fund_size_aum,
            "expense_ratio": self.expense_ratio,
            "rating": self.rating,
        }
        canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["facts_hash"] = self.facts_hash()
        return data

    def front_matter_snippet(self) -> dict[str, str]:
        """Flat keys for YAML front matter."""
        out: dict[str, str] = {}
        if self.nav:
            out["nav_display"] = str(self.nav.get("display", ""))
            if self.nav.get("as_of_iso"):
                out["nav_as_of"] = str(self.nav["as_of_iso"])
        if self.minimum_sip:
            out["minimum_sip_display"] = str(self.minimum_sip.get("display", ""))
        if self.fund_size_aum:
            out["fund_size_aum_display"] = str(self.fund_size_aum.get("display", ""))
        if self.expense_ratio:
            out["expense_ratio_display"] = str(self.expense_ratio.get("display", ""))
        if self.rating:
            out["rating_display"] = str(self.rating.get("display", ""))
        out["facts_hash"] = self.facts_hash()
        return out

    def metrics_markdown(self) -> str:
        """## Key fund metrics table for corpus body."""
        rows: list[tuple[str, str]] = []

        if self.nav:
            label = "NAV"
            if self.nav.get("as_of_display"):
                label = f"NAV (as of {self.nav['as_of_display']})"
            rows.append((label, str(self.nav.get("display", "—"))))
        else:
            rows.append(("NAV", "—"))

        rows.append(
            ("Minimum SIP", str((self.minimum_sip or {}).get("display", "—")))
        )
        rows.append(
            ("Fund size (AUM)", str((self.fund_size_aum or {}).get("display", "—")))
        )
        rows.append(
            ("Expense ratio", str((self.expense_ratio or {}).get("display", "—")))
        )
        rows.append(("Rating", str((self.rating or {}).get("display", "—"))))

        lines = ["## Key fund metrics", "", "| Metric | Value |", "|--------|-------|"]
        for metric, value in rows:
            lines.append(f"| {metric} | {value} |")
        return "\n".join(lines) + "\n\n"


def _parse_inr_amount(text: str) -> float | None:
    cleaned = text.replace("₹", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _parse_percent(text: str) -> float | None:
    m = re.search(r"([\d.]+)\s*%", text)
    if m:
        return float(m.group(1))
    return None


def _parse_cr(text: str) -> float | None:
    m = re.search(r"([\d,]+(?:\.\d+)?)\s*Cr", text, re.I)
    if m:
        return float(m.group(1).replace(",", ""))
    return None


def _value_after_label(soup: BeautifulSoup, label: str) -> str | None:
    """Find exact label text on Groww and return associated value."""
    node = soup.find(string=lambda t: t and t.strip() == label)
    if not node:
        return None

    parent = node.parent
    # Value is often in the next element sibling with a "Heavy" or numeric class
    for sibling in parent.next_siblings:
        if getattr(sibling, "get_text", None):
            text = sibling.get_text(strip=True)
            if text and text != label:
                return text

    # Fallback: parent container text minus label
    container = parent.parent
    if container:
        block = container.get_text(" ", strip=True)
        block = re.sub(r"^" + re.escape(label) + r"\s*", "", block).strip()
        # take first token group that looks like a value
        if block:
            return block.split("  ")[0].strip() if "  " in block else block[:40]

    return None


def _extract_nav(soup: BeautifulSoup) -> dict[str, Any] | None:
    # Groww shows "NAV: 18 May '26" and amount nearby
    nav_date_node = soup.find(string=re.compile(r"NAV:\s*.+", re.I))
    if not nav_date_node:
        return None

    as_of_display = re.sub(r"^NAV:\s*", "", nav_date_node.strip(), flags=re.I).strip()
    container = nav_date_node.find_parent("div")
    amount_display = None
    for _ in range(6):
        if not container:
            break
        text = container.get_text(" ", strip=True)
        inr = re.search(r"₹\s*[\d,]+(?:\.\d+)?", text)
        if inr:
            amount_display = inr.group(0).replace(" ", "")
            break
        container = container.parent

    if not amount_display:
        return None

    as_of_iso = None
    dm = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+'?(\d{2,4})", as_of_display)
    if dm:
        # best-effort; full parsing optional
        as_of_iso = as_of_display

    return {
        "display": amount_display,
        "amount_inr": _parse_inr_amount(amount_display),
        "as_of_display": as_of_display,
        "as_of_iso": as_of_iso,
    }


def _build_metric_field(label: str, raw: str | None) -> dict[str, Any] | None:
    if not raw:
        return None

    raw = raw.strip()
    if label == "expense_ratio":
        pct = _parse_percent(raw)
        return {"display": raw if "%" in raw else f"{raw}%", "percent": pct}
    if label == "minimum_sip":
        amt = _parse_inr_amount(raw)
        return {"display": raw, "amount_inr": amt}
    if label == "fund_size_aum":
        return {
            "display": raw,
            "amount_cr": _parse_cr(raw),
        }
    if label == "rating":
        m = re.search(r"(\d+(?:\.\d+)?)", raw)
        val = float(m.group(1)) if m else None
        return {"display": raw, "value": val}

    return {"display": raw}


def extract_fund_facts(
    html: str,
    scheme_id: str,
    scheme_name: str,
    source_url: str,
    content_captured_at: str,
    scrape_run_id: str,
) -> FundFacts:
    soup = BeautifulSoup(html, "lxml")
    facts = FundFacts(
        scheme_id=scheme_id,
        scheme_name=scheme_name,
        source_url=source_url,
        content_captured_at=content_captured_at,
        scrape_run_id=scrape_run_id,
    )

    facts.nav = _extract_nav(soup)

    for groww_label, field_name in _LABEL_MAP.items():
        raw = _value_after_label(soup, groww_label)
        metric = _build_metric_field(field_name, raw)
        setattr(facts, field_name, metric)
        if metric is None:
            facts.missing_fields.append(field_name)

    if facts.nav is None:
        facts.missing_fields.append("nav")

    required = {"nav", "minimum_sip", "fund_size_aum", "expense_ratio", "rating"}
    present = required - set(facts.missing_fields)
    if present == required:
        facts.extraction_status = "complete"
    elif present:
        facts.extraction_status = "partial"
    else:
        facts.extraction_status = "failed"

    return facts
