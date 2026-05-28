from __future__ import annotations

import os
from pathlib import Path

from phases.p0_scrape.models import ScrapeRunResult


def write_github_outputs(run: ScrapeRunResult, output_file: str | None = None) -> None:
    """Write workflow outputs for downstream jobs (corpus_changed, etc.)."""
    path_str = (output_file or os.environ.get("GITHUB_OUTPUT", "")).strip()
    if not path_str or path_str == ".":
        return
    path = Path(path_str)

    lines = [
        f"corpus_changed={'true' if run.corpus_changed else 'false'}",
        f"scrape_run_id={run.scrape_run_id}",
        f"success_count={run.success_count}",
        f"failed_count={run.failed_count}",
    ]
    with path.open("a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_step_summary(run: ScrapeRunResult) -> None:
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    rows = "\n".join(
        f"| {r.scheme_id} | {r.status} | {r.hash_changed} | {r.error or '-'} |"
        for r in run.results
    )
    body = f"""## Scrape run `{run.scrape_run_id}`

- **corpus_changed**: {run.corpus_changed}
- **success / failed**: {run.success_count} / {run.failed_count}

| Scheme | Status | Hash changed | Error |
|--------|--------|--------------|-------|
{rows}
"""
    Path(summary_path).write_text(body, encoding="utf-8")
