"""Production runtime toggles (e.g. Render free tier memory limits)."""

from __future__ import annotations

import os


def api_sparse_only() -> bool:
    """
    Use BM25-only retrieval on the API (no local embedding model / Chroma query).

    Defaults to True on Render where the free instance has ~512MB RAM and cannot
    load sentence-transformers + PyTorch alongside the rest of the stack.
  """
    explicit = os.environ.get("API_SPARSE_ONLY", "").strip().lower()
    if explicit in ("1", "true", "yes", "on"):
        return True
    if explicit in ("0", "false", "no", "off"):
        return False
    return bool(os.environ.get("RENDER"))
