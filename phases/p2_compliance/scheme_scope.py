from __future__ import annotations

from phases.common.config_loader import load_sources_config

_IN_SCOPE_IDS: set[str] | None = None


def in_scope_scheme_ids() -> set[str]:
    global _IN_SCOPE_IDS
    if _IN_SCOPE_IDS is None:
        _IN_SCOPE_IDS = {s.scheme_id for s in load_sources_config().sources}
    return _IN_SCOPE_IDS


def detect_scheme_id(query: str) -> str | None:
    from runtime.phase_5_retrieval.scheme_resolution import resolve_scheme

    return resolve_scheme(query).scheme_id


def is_in_scope_scheme(scheme_id: str | None) -> bool:
    return scheme_id is not None and scheme_id in in_scope_scheme_ids()
