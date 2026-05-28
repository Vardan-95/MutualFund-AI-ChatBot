#!/usr/bin/env python3
"""CLI entrypoint for Groww scraping (GitHub Actions + local)."""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from phases.p0_scrape import run_scrape
from phases.p0b_scheduler.gha_outputs import write_github_outputs, write_step_summary

load_project_env()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scrape Groww scheme pages into data/corpus/")
    parser.add_argument(
        "--scheme",
        action="append",
        dest="schemes",
        metavar="SCHEME_ID",
        help="Scrape only these scheme_id values (repeatable)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print run result as JSON to stdout",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        default=True,
        help="Exit 1 if any scheme failed (default: true)",
    )
    parser.add_argument(
        "--no-fail-on-error",
        action="store_false",
        dest="fail_on_error",
        help="Exit 0 even if some schemes failed",
    )
    args = parser.parse_args(argv)

    run = run_scrape(scheme_ids=args.schemes)
    write_github_outputs(run)
    write_step_summary(run)

    if args.json:
        print(
            json.dumps(
                {
                    "scrape_run_id": run.scrape_run_id,
                    "content_captured_at": run.content_captured_at,
                    "corpus_changed": run.corpus_changed,
                    "success_count": run.success_count,
                    "failed_count": run.failed_count,
                    "results": [
                        {
                            "scheme_id": r.scheme_id,
                            "status": r.status,
                            "hash_changed": r.hash_changed,
                            "content_hash": r.content_hash,
                            "error": r.error,
                        }
                        for r in run.results
                    ],
                },
                indent=2,
            )
        )
    else:
        print(f"Scrape run {run.scrape_run_id}")
        print(f"  corpus_changed: {run.corpus_changed}")
        print(f"  success: {run.success_count}, failed: {run.failed_count}")
        for r in run.results:
            flag = " [CHANGED]" if r.hash_changed else ""
            err = f" — {r.error}" if r.error else ""
            print(f"  - {r.scheme_id}: {r.status}{flag}{err}")

    if args.fail_on_error and run.failed_count > 0:
        return 1
    return 0
