from __future__ import annotations

import os
import uuid
from datetime import date
from pathlib import Path

from phases.common.config_loader import (
    SchemeSource,
    SourcesConfig,
    ScraperConfig,
    load_scraper_config,
    load_sources_config,
)
from phases.common.paths import PROJECT_ROOT, resolve_path
from phases.p0_scrape.extractor import body_content_hash, extract_markdown_body
from phases.p0_scrape.facts_extractor import extract_fund_facts
from phases.p0_scrape.facts_store import save_scheme_facts
from phases.p0_scrape.parallel_fetcher import ParallelGrowwFetcher
from phases.p0_scrape.manifest import (
    get_previous_facts_hash as manifest_previous_facts_hash,
    get_previous_hash,
    load_manifest,
    save_manifest,
)
from phases.p0_scrape.models import SchemeScrapeResult, ScrapeRunResult
from phases.p0_scrape.writer import (
    archive_raw_html,
    compose_corpus_body,
    write_corpus_markdown,
)


class ScrapeService:
    def __init__(
        self,
        sources: SourcesConfig | None = None,
        scraper: ScraperConfig | None = None,
    ) -> None:
        self.sources = sources or load_sources_config()
        self.scraper = scraper or load_scraper_config()
        self.fetcher = ParallelGrowwFetcher(self.scraper)
        self.manifest_path = resolve_path(self.scraper.manifest_path)
        self.raw_base = PROJECT_ROOT / self.scraper.raw_html_path

    def scrape_scheme(
        self,
        source: SchemeSource,
        scrape_run_id: str,
        content_captured_at: str,
        manifest: dict,
        prefetched: tuple[str, str] | None = None,
    ) -> SchemeScrapeResult:
        previous_hash = get_previous_hash(manifest, source.scheme_id)
        previous_facts_hash = manifest_previous_facts_hash(manifest, source.scheme_id)
        result = SchemeScrapeResult(
            scheme_id=source.scheme_id,
            source_url=source.source_url,
            status="failed",
            previous_hash=previous_hash,
            previous_facts_hash=previous_facts_hash,
            corpus_file=source.corpus_file,
        )

        try:
            if prefetched is None:
                _, final_url, html = self.fetcher.fetch_one(source)
            else:
                final_url, html = prefetched
            if final_url != source.source_url:
                result.source_url = final_url

            facts = extract_fund_facts(
                html,
                scheme_id=source.scheme_id,
                scheme_name=source.scheme_name,
                source_url=final_url,
                content_captured_at=content_captured_at,
                scrape_run_id=scrape_run_id,
            )
            save_scheme_facts(facts)

            supplemental = extract_markdown_body(html, final_url)
            body = compose_corpus_body(facts, supplemental)
            content_hash = body_content_hash(body)

            if self.scraper.raw_html_archive:
                archive_raw_html(
                    self.raw_base,
                    source.scheme_id,
                    date.fromisoformat(content_captured_at),
                    html,
                )

            write_corpus_markdown(
                source,
                self.sources,
                body,
                content_captured_at,
                scrape_run_id,
                content_hash,
                facts=facts,
            )

            result.status = "success"
            result.content_hash = content_hash
            result.hash_changed = previous_hash != content_hash
            result.facts_hash = facts.facts_hash()
            result.facts_hash_changed = previous_facts_hash != result.facts_hash
            result.facts_status = facts.extraction_status
            return result

        except Exception as exc:
            result.error = str(exc)
            return result

    def scrape_all(
        self,
        scheme_ids: list[str] | None = None,
        scrape_run_id: str | None = None,
    ) -> ScrapeRunResult:
        run_id = scrape_run_id or os.environ.get("GITHUB_RUN_ID") or str(uuid.uuid4())
        captured = date.today().isoformat()

        run = ScrapeRunResult(
            scrape_run_id=run_id,
            content_captured_at=captured,
        )

        manifest = load_manifest(self.manifest_path)
        targets = self.sources.sources
        if scheme_ids:
            id_set = set(scheme_ids)
            targets = [s for s in targets if s.scheme_id in id_set]

        prefetched: dict[str, tuple[str, str]] = {}
        try:
            prefetched = self.fetcher.fetch_all(targets)
        except Exception:
            # Keep partial-success behavior: fallback to per-scheme fetch inside scrape_scheme.
            prefetched = {}

        for source in targets:
            run.results.append(
                self.scrape_scheme(
                    source,
                    run_id,
                    captured,
                    manifest,
                    prefetched=prefetched.get(source.scheme_id),
                )
            )

        run.compute_summary()
        save_manifest(self.manifest_path, run, manifest)
        return run


def run_scrape(
    scheme_ids: list[str] | None = None,
    scrape_run_id: str | None = None,
) -> ScrapeRunResult:
    return ScrapeService().scrape_all(scheme_ids=scheme_ids, scrape_run_id=scrape_run_id)
