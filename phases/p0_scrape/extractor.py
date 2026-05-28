from __future__ import annotations

import re

import trafilatura
from markdownify import markdownify as html_to_md

# Lines/patterns to drop from Groww page chrome
_BOILERPLATE_PATTERNS = [
    re.compile(r"^Invest in Stocks", re.I),
    re.compile(r"^Mutual Fund Houses", re.I),
    re.compile(r"^SIP calculator", re.I),
    re.compile(r"^Stock Screener", re.I),
    re.compile(r"^Trade in Futures", re.I),
    re.compile(r"^Start SIP", re.I),
    re.compile(r"^Compare Funds", re.I),
    re.compile(r"^Track Funds", re.I),
    re.compile(r"^Pricing$", re.I),
    re.compile(r"^Blog$", re.I),
]


def _strip_script_artifacts(text: str) -> str:
    """Remove JS bundles that markdownify can pull from Groww pages."""
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if re.search(r"\b(function|Promise|const |let |var |=>)\b", stripped):
            continue
        if stripped.startswith("if (") or "document." in stripped or "window." in stripped:
            continue
        lines.append(line)
    return "\n".join(lines)


def _strip_boilerplate(text: str) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue
        if any(p.search(stripped) for p in _BOILERPLATE_PATTERNS):
            continue
        if stripped in {"Stocks", "F&O", "Mutual Funds", "More"}:
            continue
        lines.append(line)

    body = "\n".join(lines)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body.strip()


def _table_heavy(text: str) -> bool:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 5:
        return False
    pipe_lines = sum(1 for ln in lines if "|" in ln)
    return pipe_lines / len(lines) > 0.5


def extract_markdown_body(html: str, page_url: str) -> str:
    """Extract main content from Groww HTML as Markdown."""
    md_fallback = html_to_md(
        html,
        heading_style="ATX",
        strip=["script", "style", "nav", "footer"],
    )
    md_fallback = _strip_boilerplate(md_fallback)

    extracted = trafilatura.extract(
        html,
        url=page_url,
        include_tables=True,
        include_links=False,
        output_format="txt",
    )

    if extracted and len(extracted.strip()) > 200 and not _table_heavy(extracted):
        text = extracted
    elif len(md_fallback.strip()) > 200:
        text = md_fallback
    elif extracted:
        text = f"{extracted}\n\n{md_fallback}"
    else:
        text = md_fallback

    text = _strip_boilerplate(text)
    text = _strip_script_artifacts(text)

    if len(text.strip()) < 100:
        raise ValueError("Extracted content too short; page structure may have changed")

    return _extract_heading_sections(text)


def _extract_heading_sections(text: str) -> str:
    """Keep markdown headings and tables; drop inline JS / nav blobs."""
    kept: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if s.startswith("#") or s.startswith("|"):
            kept.append(line)
        elif len(s) < 120 and not re.search(r"\b(global|Promise|function)\b", s):
            kept.append(line)
    return "\n".join(kept).strip()


def body_content_hash(normalized_body: str) -> str:
    import hashlib

    return hashlib.sha256(normalized_body.encode("utf-8")).hexdigest()
