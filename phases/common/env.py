"""Load `.env` from the repository root into os.environ."""

from __future__ import annotations

import os
from pathlib import Path

from phases.common.paths import PROJECT_ROOT


def load_project_env() -> Path | None:
    """Load `.env` if present. Returns the path loaded, or None if skipped."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return None
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None
    load_dotenv(env_path, override=False)
    return env_path


def require_chroma_app_env() -> None:
    """Raise if Chroma Cloud app credentials are missing."""
    missing = [
        name
        for name in ("CHROMA_API_KEY", "CHROMA_TENANT", "CHROMA_DATABASE")
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise RuntimeError(
            "Missing Chroma Cloud variables in .env: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill values from trychroma.com → Connect."
        )
