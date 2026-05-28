"""CLI: python -m pipeline.ingest [--step all|chunk|embed|bm25|validate]

Run via: python -m pipeline
"""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from pipeline.ingest import run_ingest

load_project_env()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Ingest corpus into chunk + vector + BM25 indexes")
    parser.add_argument(
        "--step",
        default="all",
        choices=["all", "load", "chunk", "embed", "bm25", "validate"],
        help="Pipeline step to run",
    )
    parser.add_argument("--force", action="store_true", help="Run even if scrape reported no changes")
    parser.add_argument("--force-reembed", action="store_true", help="Bypass embedding cache")
    parser.add_argument("--json", action="store_true", help="Print result as JSON")
    args = parser.parse_args(argv)

    try:
        result = run_ingest(
            step=None if args.step == "all" else args.step,
            force=args.force,
            force_reembed=args.force_reembed,
        )
    except Exception as exc:
        print(f"INGEST FAILED: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(
            json.dumps(
                {
                    "skipped": result.skipped,
                    "corpus_version": result.corpus_version,
                    "chunk_count": result.chunk_count,
                    "schemes": result.schemes,
                    "skipped_embed_cache": result.skipped_embed_cache,
                },
                indent=2,
            )
        )
    else:
        if result.skipped:
            print("Ingest skipped (no corpus changes).")
        else:
            print(f"Ingest complete: corpus_version={result.corpus_version}, chunks={result.chunk_count}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
