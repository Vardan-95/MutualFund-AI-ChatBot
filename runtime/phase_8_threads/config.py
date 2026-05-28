from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from phases.common.paths import PROJECT_ROOT


@dataclass(frozen=True)
class ThreadConfig:
    db_path: Path
    max_turns: int
    expand_followups: bool


def load_thread_config() -> ThreadConfig:
    db = os.environ.get("THREAD_DB_PATH", "data/threads/threads.db")
    max_turns = int(os.environ.get("THREAD_MAX_TURNS", "4"))
    expand = os.environ.get("THREAD_EXPAND_QUERY", "true").strip().lower() not in (
        "0",
        "false",
        "no",
    )
    return ThreadConfig(
        db_path=PROJECT_ROOT / db,
        max_turns=max(1, min(max_turns, 12)),
        expand_followups=expand,
    )
