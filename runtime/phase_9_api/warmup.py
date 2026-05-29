"""Preload RAG stack on API startup so first chat request stays within proxy timeouts."""

from __future__ import annotations

import logging
import os
import threading
import time
from typing import Literal

from phases.common.paths import PROJECT_ROOT

logger = logging.getLogger(__name__)

WarmupStatus = Literal["pending", "loading", "ready", "failed"]

_lock = threading.Lock()
_status: WarmupStatus = "pending"
_error: str | None = None
_started_at: float | None = None
_ready_at: float | None = None


def get_warmup_state() -> dict:
    with _lock:
        out: dict = {"status": _status}
        if _error:
            out["error"] = _error
        if _started_at is not None:
            out["started_at"] = _started_at
        if _ready_at is not None:
            out["ready_at"] = _ready_at
            out["load_seconds"] = round(_ready_at - _started_at, 2)
        return out


def _configure_model_cache() -> None:
    cache = PROJECT_ROOT / "data" / "models"
    cache.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(cache))
    os.environ.setdefault("HF_HOME", str(cache))


def _run_warmup() -> None:
    global _status, _error, _ready_at
    try:
        _configure_model_cache()
        from runtime.phase_7_safety.answer import warmup_rag_stack

        warmup_rag_stack()
        with _lock:
            _status = "ready"
            _ready_at = time.perf_counter()
        logger.info("RAG warmup finished in %.1fs", _ready_at - (_started_at or _ready_at))
    except Exception as exc:
        logger.exception("RAG warmup failed")
        with _lock:
            _status = "failed"
            _error = str(exc)


def start_warmup_background() -> None:
    global _status, _started_at
    with _lock:
        if _status in ("loading", "ready"):
            return
        if os.environ.get("SKIP_RAG_WARMUP", "").strip().lower() in ("1", "true", "yes"):
            _status = "ready"
            return
        _status = "loading"
        _started_at = time.perf_counter()

    thread = threading.Thread(target=_run_warmup, name="rag-warmup", daemon=True)
    thread.start()


def ensure_warmup_started() -> None:
    start_warmup_background()
