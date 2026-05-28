"""CLI: python -m runtime.phase_7_safety "…" | python -m runtime.phase_7_safety --route-only "…"."""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from runtime.phase_7_safety.answer import answer
from runtime.phase_7_safety.router import route_query

load_project_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 7 safety / full RAG answer")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--route-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    q = " ".join(args.query)

    if args.route_only:
        routed = route_query(q)
        payload = {
            "intent": routed.intent.intent,
            "scheme_id": routed.intent.scheme_id,
            "refusal": routed.intent.refusal,
            "refusal_message": routed.intent.refusal_message,
            "education_url": routed.intent.education_url,
            "matched_by": routed.intent.matched_by,
            "blocked_before_retrieval": routed.blocked_before_retrieval,
        }
        if args.json:
            print(json.dumps(payload, indent=2))
        else:
            print(
                f"intent={payload['intent']} refusal={payload['refusal']} "
                f"blocked_before_retrieval={payload['blocked_before_retrieval']}"
            )
            if payload["refusal_message"]:
                print(payload["refusal_message"])
        return 0

    result = answer(q)
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
                    "guardrail_flags": result.guardrail_flags,
                },
                indent=2,
            )
        )
    else:
        print(result.answer)
        if result.source_url:
            print(f"\nCitation: {result.source_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
