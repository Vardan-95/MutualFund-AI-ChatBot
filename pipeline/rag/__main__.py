"""CLI: python -m pipeline.rag "What is the minimum SIP for HDFC Large Cap Fund?" """

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from pipeline.rag.orchestrator import run_query

load_project_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a single RAG query (P1)")
    parser.add_argument("query", nargs="+", help="User question")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    q = " ".join(args.query)
    result = run_query(q)
    if args.json:
        print(
            json.dumps(
                {
                    "answer": result.answer,
                    "intent": result.intent,
                    "source_url": result.source_url,
                    "content_captured_at": result.content_captured_at,
                    "corpus_version": result.corpus_version,
                    "chunk_ids": result.chunk_ids,
                    "refused": result.refused,
                    "education_url": result.education_url,
                    "intent_matched_by": result.intent_matched_by,
                    "guardrail_flags": result.guardrail_flags,
                },
                indent=2,
            )
        )
    else:
        print(result.answer)
        if result.source_url:
            print(f"\nCitation: {result.source_url}")
        if result.disclaimer:
            print(f"\n{result.disclaimer}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
