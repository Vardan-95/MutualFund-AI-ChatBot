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
    cors_origin_regex: str | None


def _truthy(name: str, default: str = "false") -> bool:
    return os.environ.get(name, default).strip().lower() in ("1", "true", "yes", "on")


def _default_api_host() -> str:
    """Local dev binds loopback; PaaS (Render/Heroku) sets PORT and requires 0.0.0.0."""
    explicit = os.environ.get("API_HOST", "").strip()
    if explicit:
        return explicit
    if os.environ.get("PORT"):
        return "0.0.0.0"
    return "127.0.0.1"


def load_api_config() -> ApiConfig:
    cors_raw = os.environ.get(
        "API_CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).strip()
    origins = [o.strip() for o in cors_raw.split(",") if o.strip()]
    cors_regex: str | None = None
    if _truthy("API_CORS_ALLOW_VERCEL_PREVIEWS"):
        cors_regex = r"https://.*\.vercel\.app"
    secret = os.environ.get("ADMIN_REINDEX_SECRET", "").strip() or None
    return ApiConfig(
        host=_default_api_host(),
        port=int(os.environ.get("PORT", "8080")),
        debug_responses=_truthy("RUNTIME_API_DEBUG"),
        admin_reindex_secret=secret,
        cors_origins=origins,
        cors_origin_regex=cors_regex,
    )
