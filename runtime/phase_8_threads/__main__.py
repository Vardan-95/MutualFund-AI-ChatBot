"""CLI for phase 8 threads."""

from __future__ import annotations

import argparse
import json
import sys

from phases.common.env import load_project_env
from runtime.phase_8_threads.service import ThreadService

load_project_env()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 8 multi-thread chat CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("new-thread", help="Create a thread UUID")
    p_say = sub.add_parser("say", help="Post user message and get answer")
    p_say.add_argument("thread_id")
    p_say.add_argument("message", nargs="+")
    p_hist = sub.add_parser("history", help="Show thread messages")
    p_hist.add_argument("thread_id")
    p_ctx = sub.add_parser("context", help="Show RAG context window")
    p_ctx.add_argument("thread_id")
    sub.add_parser("list-threads", help="List recent threads")

    args = parser.parse_args(argv)
    svc = ThreadService()

    if args.cmd == "new-thread":
        t = svc.new_thread()
        print(t.thread_id)
        return 0

    if args.cmd == "list-threads":
        for t in svc.list_threads():
            print(f"{t.thread_id}  updated={t.updated_at}")
        return 0

    if args.cmd == "history":
        for m in svc.history(args.thread_id):
            print(f"[{m.timestamp}] {m.role}: {m.content[:200]}")
        return 0

    if args.cmd == "context":
        ctx = svc.context_for_rag(args.thread_id)
        print(ctx or "(empty)")
        return 0

    if args.cmd == "say":
        result, thread = svc.post_user_message(
            args.thread_id,
            " ".join(args.message),
        )
        print(
            json.dumps(
                {
                    "thread_id": thread.thread_id,
                    "answer": result.answer,
                    "source_url": result.source_url,
                    "intent": result.intent,
                },
                indent=2,
            )
        )
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
