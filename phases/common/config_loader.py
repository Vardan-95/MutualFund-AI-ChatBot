from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from phases.common.paths import CONFIG_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class SchemeSource:
    scheme_id: str
    scheme_name: str
    scheme_category: str
    source_url: str
    corpus_file: str
    document_type: str = "groww_scheme_page"

    @property
    def corpus_path(self) -> Path:
        return PROJECT_ROOT / self.corpus_file


@dataclass(frozen=True)
class SourcesConfig:
    amc_name: str
    sources: list[SchemeSource]


@dataclass(frozen=True)
class ScraperConfig:
    allowed_domains: list[str]
    request_delay_seconds: float
    max_concurrent: int
    timeout_connect_seconds: float
    timeout_read_seconds: float
    max_retries: int
    retry_backoff_seconds: float
    raw_html_archive: bool
    raw_html_path: str
    user_agent: str
    corpus_path: str
    manifest_path: str


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_sources_config(path: Path | None = None) -> SourcesConfig:
    data = load_yaml(path or CONFIG_DIR / "sources.yaml")
    amc = data.get("amc", {})
    sources = [
        SchemeSource(
            scheme_id=s["scheme_id"],
            scheme_name=s["scheme_name"],
            scheme_category=s["scheme_category"],
            source_url=s["source_url"],
            corpus_file=s["corpus_file"],
            document_type=s.get("document_type", "groww_scheme_page"),
        )
        for s in data.get("sources", [])
    ]
    return SourcesConfig(amc_name=amc.get("name", "HDFC Mutual Fund"), sources=sources)


def load_scraper_config(path: Path | None = None) -> ScraperConfig:
    data = load_yaml(path or CONFIG_DIR / "scraper.yaml")
    return ScraperConfig(
        allowed_domains=list(data.get("allowed_domains", ["groww.in"])),
        request_delay_seconds=float(data.get("request_delay_seconds", 1.5)),
        max_concurrent=int(data.get("max_concurrent", 2)),
        timeout_connect_seconds=float(data.get("timeout_connect_seconds", 10)),
        timeout_read_seconds=float(data.get("timeout_read_seconds", 30)),
        max_retries=int(data.get("max_retries", 3)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", 2)),
        raw_html_archive=bool(data.get("raw_html_archive", True)),
        raw_html_path=str(data.get("raw_html_path", "data/raw")),
        user_agent=str(
            data.get(
                "user_agent",
                "MutualFundFAQBot/1.0 (+https://github.com; facts-only corpus refresh)",
            )
        ),
        corpus_path=str(data.get("corpus_path", "data/corpus")),
        manifest_path=str(data.get("manifest_path", "data/index/ingestion_manifest.json")),
    )
