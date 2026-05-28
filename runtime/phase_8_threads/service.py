from __future__ import annotations

import json

from pipeline.rag.models import RAGResponse
from runtime.phase_7_safety.answer import answer
from runtime.phase_8_threads.config import ThreadConfig, load_thread_config
from runtime.phase_8_threads.expand import expand_query_from_history, is_followup_query
from runtime.phase_8_threads.store import SqliteThreadStore, ThreadMessage, ThreadRecord


class ThreadService:
    def __init__(self, cfg: ThreadConfig | None = None) -> None:
        self.cfg = cfg or load_thread_config()
        self.store = SqliteThreadStore(self.cfg.db_path)

    def new_thread(self, session_key: str | None = None) -> ThreadRecord:
        return self.store.new_thread(session_key=session_key)

    def list_threads(self, session_key: str | None = None) -> list[ThreadRecord]:
        return self.store.list_threads(session_key=session_key)

    def history(self, thread_id: str) -> list[ThreadMessage]:
        return self.store.history(thread_id)

    def update_thread(
        self,
        thread_id: str,
        *,
        title: str | None = None,
        pinned: bool | None = None,
    ) -> ThreadRecord | None:
        return self.store.update_thread(thread_id, title=title, pinned=pinned)

    def delete_thread(self, thread_id: str) -> bool:
        return self.store.delete_thread(thread_id)

    def context_for_rag(self, thread_id: str) -> str | None:
        lines = self.store.recent_user_lines(thread_id, self.cfg.max_turns)
        if not lines:
            return None
        return "\n".join(lines)

    def post_user_message(
        self,
        thread_id: str,
        query: str,
        *,
        session_key: str | None = None,
    ) -> tuple[RAGResponse, ThreadRecord]:
        thread = self.store.get_or_create(thread_id, session_key=session_key)
        thread_id = thread.thread_id

        prior_user = self.store.recent_user_lines(thread_id, self.cfg.max_turns)
        effective_query = query
        followup = self.cfg.expand_followups and bool(prior_user) and is_followup_query(query)
        if followup:
            effective_query = expand_query_from_history(query, prior_user)

        # Inject prior context only for follow-up style prompts to avoid
        # contaminating unrelated new questions with previous turns.
        context = self.context_for_rag(thread_id) if followup else None
        self.store.append_message(thread_id, "user", query)

        result = answer(effective_query, thread_context=context)

        debug_id = None
        if result.chunk_ids:
            debug_id = json.dumps(
                {
                    "chunk_ids": result.chunk_ids,
                    "intent": result.intent,
                    "flags": result.guardrail_flags,
                }
            )[:500]

        self.store.append_message(
            thread_id,
            "assistant",
            result.answer,
            retrieval_debug_id=debug_id,
        )

        updated = self.store.get_thread(thread_id) or thread
        return result, updated


thread_service = ThreadService()
