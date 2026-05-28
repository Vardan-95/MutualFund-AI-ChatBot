from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from phases.common.paths import PROJECT_ROOT
from phases.p0_scrape.facts_extractor import FundFacts


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def facts_dir() -> Path:
    path = PROJECT_ROOT / "data" / "facts"
    path.mkdir(parents=True, exist_ok=True)
    (path / "by_scheme").mkdir(parents=True, exist_ok=True)
    return path


def load_aggregate_facts(path: Path | None = None) -> dict[str, Any]:
    path = path or facts_dir() / "scheme_facts.json"
    if not path.exists():
        return {"version": 1, "schemes": {}}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def save_scheme_facts(facts: FundFacts) -> Path:
    """Persist per-scheme JSON and update aggregate scheme_facts.json."""
    base = facts_dir()
    scheme_path = base / "by_scheme" / f"{facts.scheme_id}.json"
    scheme_path.write_text(
        json.dumps(facts.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    aggregate = load_aggregate_facts(base / "scheme_facts.json")
    aggregate["version"] = 1
    aggregate["scrape_run_id"] = facts.scrape_run_id
    aggregate["content_captured_at"] = facts.content_captured_at
    aggregate["updated_at"] = _now_iso()
    aggregate.setdefault("schemes", {})[facts.scheme_id] = facts.to_dict()

    agg_path = base / "scheme_facts.json"
    agg_path.write_text(
        json.dumps(aggregate, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return scheme_path


def get_previous_facts_hash(manifest: dict[str, Any], scheme_id: str) -> str | None:
    entry = manifest.get("schemes", {}).get(scheme_id, {})
    return entry.get("facts_hash")
