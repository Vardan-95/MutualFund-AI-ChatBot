from __future__ import annotations

from datetime import date
from pathlib import Path

import frontmatter

from phases.common.config_loader import SchemeSource, SourcesConfig
from phases.p0_scrape.facts_extractor import FundFacts


def build_front_matter(
    source: SchemeSource,
    amc_name: str,
    content_captured_at: str,
    scrape_run_id: str,
    content_hash: str,
    facts: FundFacts | None = None,
) -> dict:
    meta = {
        "source_url": source.source_url,
        "scheme_name": source.scheme_name,
        "scheme_id": source.scheme_id,
        "amc_name": amc_name,
        "scheme_category": source.scheme_category,
        "document_type": source.document_type,
        "content_captured_at": content_captured_at,
        "scrape_run_id": scrape_run_id,
        "content_hash": content_hash,
    }
    if facts:
        meta.update(facts.front_matter_snippet())
        meta["facts_extraction_status"] = facts.extraction_status
        if facts.missing_fields:
            meta["facts_missing_fields"] = facts.missing_fields
    return meta


def compose_corpus_body(facts: FundFacts, supplemental_body: str) -> str:
    """Key metrics first, then remaining page content."""
    metrics = facts.metrics_markdown()
    supplemental = supplemental_body.strip()
    if supplemental.startswith("## Key fund metrics"):
        return supplemental + "\n"
    return metrics + supplemental


def write_corpus_markdown(
    source: SchemeSource,
    sources_config: SourcesConfig,
    body: str,
    content_captured_at: str,
    scrape_run_id: str,
    content_hash: str,
    facts: FundFacts | None = None,
) -> Path:
    post = frontmatter.Post(
        body,
        **build_front_matter(
            source,
            sources_config.amc_name,
            content_captured_at,
            scrape_run_id,
            content_hash,
            facts=facts,
        ),
    )
    path = source.corpus_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(frontmatter.dumps(post), encoding="utf-8")
    return path


def archive_raw_html(
    raw_base: Path,
    scheme_id: str,
    captured_date: date,
    html: str,
) -> Path:
    archive_dir = raw_base / scheme_id / captured_date.isoformat()
    archive_dir.mkdir(parents=True, exist_ok=True)
    path = archive_dir / "page.html"
    path.write_text(html, encoding="utf-8")
    return path
