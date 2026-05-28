from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases.p0_scrape.models import ScrapeRunResult


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def load_manifest(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"schemes": {}, "corpus_version": 0}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def get_previous_hash(manifest: dict[str, Any], scheme_id: str) -> str | None:
    entry = manifest.get("schemes", {}).get(scheme_id)
    if entry:
        return entry.get("content_hash")
    return None


def get_previous_facts_hash(manifest: dict[str, Any], scheme_id: str) -> str | None:
    entry = manifest.get("schemes", {}).get(scheme_id)
    if entry:
        return entry.get("facts_hash")
    return None


def save_manifest(path: Path, run: ScrapeRunResult, manifest: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)

    schemes = manifest.setdefault("schemes", {})
    for result in run.results:
        schemes[result.scheme_id] = {
            "source_url": result.source_url,
            "status": result.status,
            "content_hash": result.content_hash,
            "hash_changed": result.hash_changed,
            "facts_hash": result.facts_hash,
            "facts_hash_changed": result.facts_hash_changed,
            "facts_status": result.facts_status,
            "corpus_file": result.corpus_file,
            "error": result.error,
            "updated_at": _now_iso(),
        }

    manifest["last_scrape_run"] = {
        "scrape_run_id": run.scrape_run_id,
        "content_captured_at": run.content_captured_at,
        "completed_at": _now_iso(),
        "corpus_changed": run.corpus_changed,
        "success_count": run.success_count,
        "failed_count": run.failed_count,
        "skipped_reindex": not run.corpus_changed,
    }

    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return manifest
