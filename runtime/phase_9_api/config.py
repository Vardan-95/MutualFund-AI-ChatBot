from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ApiConfig:
    host: str
    port: int
    debug_responses: bool
    admin_reindex_secret: str | None
    cors_origins: list[str]


def _truthy(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def load_api_config() -> ApiConfig:
    cors_raw = os.environ.get(
        "API_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).strip()
    origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
    secret = os.environ.get("ADMIN_REINDEX_SECRET", "").strip() or None
    return ApiConfig(
        host=os.environ.get("API_HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8080")),
        debug_responses=_truthy("RUNTIME_API_DEBUG"),
        admin_reindex_secret=secret,
        cors_origins=origins,
    )
