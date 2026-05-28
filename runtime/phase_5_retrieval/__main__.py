"""CLI: python -m runtime.phase_5_retrieval "What is the expense ratio for HDFC Large Cap?"."""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from runtime.phase_5_retrieval.retriever import HybridRetriever

load_project_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 5 retrieval-only CLI")
    parser.add_argument("query", nargs="+", help="User question")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    q = " ".join(args.query)
    result = HybridRetriever().retrieve(q)
    payload = {
        "scheme_id": result.preprocessed.scheme.scheme_id,
        "scheme_confidence": result.preprocessed.scheme.confidence,
        "apply_scheme_filter": result.preprocessed.apply_scheme_filter,
        "numeric_conflict": result.numeric_conflict,
        "chunks": [
            {
                "chunk_id": c.chunk_id,
                "retrieval_score": round(c.retrieval_score, 4),
                "source_url": c.metadata.get("source_url"),
                "scheme_id": c.metadata.get("scheme_id"),
                "text_preview": c.text[:200].replace("\n", " "),
                "merged_chunk_ids": c.merged_chunk_ids,
            }
            for c in result.chunks
        ],
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(f"Scheme: {payload['scheme_id']} (confidence {payload['scheme_confidence']})")
        print(f"Filter applied: {payload['apply_scheme_filter']}")
        print(f"Numeric conflict: {payload['numeric_conflict']}")
        for i, ch in enumerate(payload["chunks"], 1):
            print(f"\n--- Chunk {i} (score {ch['retrieval_score']}) ---")
            print(ch["text_preview"] + "...")
            print(f"URL: {ch['source_url']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
