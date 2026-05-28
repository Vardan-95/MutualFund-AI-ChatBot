"""CLI: python -m runtime.phase_6_generation "What is the minimum SIP for HDFC Large Cap?"."""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from runtime.phase_5_retrieval.retriever import HybridRetriever
from runtime.phase_6_generation.config import load_generation_config
from runtime.phase_6_generation.context import format_footer
from runtime.phase_6_generation.generator import generate_body
from runtime.phase_5_retrieval.citation import select_citation

load_project_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 6 generation CLI (retrieve + generate)")
    parser.add_argument("query", nargs="+")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    q = " ".join(args.query)

    retrieval = HybridRetriever().retrieve(q)
    gen_cfg = load_generation_config()
    gen = generate_body(q, retrieval.chunks, cfg=gen_cfg)
    cite = select_citation(
        retrieval.chunks,
        answer=gen.body,
        scheme_id=retrieval.preprocessed.scheme.scheme_id,
        allowed_domains=["groww.in"],
    )
    footer = format_footer(cite.content_captured_at or "")

    payload = {
        "body": gen.body,
        "citation_url": cite.source_url,
        "footer": footer,
        "used_llm": gen.used_llm,
        "retried": gen.retried,
        "fallback_used": gen.fallback_used,
    }
    if args.json:
        print(json.dumps(payload, indent=2))
    else:
        print(gen.body)
        if footer:
            print(f"\n{footer}")
        if cite.source_url:
            print(f"\nCitation: {cite.source_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
