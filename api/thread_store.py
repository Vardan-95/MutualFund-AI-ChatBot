"""Thread storage — SQLite via runtime.phase_8_threads (§8)."""

from __future__ import annotations

from runtime.phase_8_threads.service import thread_service


class ThreadStoreAdapter:
    """Backward-compatible adapter for api/main.py."""

    def get_or_create(self, thread_id: str | None):
        return thread_service.store.get_or_create(thread_id)

    def append(self, thread_id: str, role: str, content: str) -> None:
        thread_service.store.append_message(thread_id, role, content)

    def context_for_rag(self, thread_id: str, max_turns: int = 2) -> str | None:
        return thread_service.context_for_rag(thread_id)


thread_store = ThreadStoreAdapter()
