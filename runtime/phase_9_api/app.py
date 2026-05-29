from __future__ import annotations

import json
import os
import time
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from phases.common.env import load_project_env
from phases.common.paths import PROJECT_ROOT
from phases.common.runtime_mode import api_sparse_only
from pipeline.rag.config import load_rag_config
from runtime.phase_8_threads.service import thread_service
from runtime.phase_9_api.config import ApiConfig, load_api_config
from runtime.phase_9_api.warmup import ensure_warmup_started, get_warmup_state, start_warmup_background
from runtime.phase_9_api.schemas import (
    AssistantMessage,
    CreateThreadRequest,
    CreateThreadResponse,
    DebugInfo,
    LegacyChatRequest,
    LegacyChatResponse,
    MessageItem,
    MessagesResponse,
    PostMessageRequest,
    PostMessageResponse,
    ThreadListResponse,
    ThreadSummary,
    UpdateThreadRequest,
)

load_project_env()
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("TRANSFORMERS_NO_JAX", "1")


@asynccontextmanager
async def _lifespan(_app: FastAPI):
    start_warmup_background()
    yield


def create_app(cfg: ApiConfig | None = None) -> FastAPI:
    cfg = cfg or load_api_config()
    app = FastAPI(
        title="Mutual Fund FAQ API",
        version="0.4.0",
        description="Phase 9 API — threads, RAG messages, health (phases 5–8).",
        lifespan=_lifespan,
    )

    if cfg.cors_origins or cfg.cors_origin_regex:
        cors_kwargs: dict = {
            "allow_credentials": True,
            "allow_methods": ["*"],
            "allow_headers": ["*"],
        }
        if cfg.cors_origins:
            cors_kwargs["allow_origins"] = cfg.cors_origins
        if cfg.cors_origin_regex:
            cors_kwargs["allow_origin_regex"] = cfg.cors_origin_regex
        app.add_middleware(CORSMiddleware, **cors_kwargs)

    @app.get("/")
    def root() -> dict:
        web_dir = PROJECT_ROOT / "web"
        return {
            "service": "mutual-fund-faq-api",
            "phase": "9",
            "docs": "/docs",
            "health": "/health",
            "threads": {
                "create": "POST /threads",
                "list": "GET /threads",
                "update": "PATCH /threads/{thread_id}",
                "delete": "DELETE /threads/{thread_id}",
                "messages": "GET /threads/{thread_id}/messages",
                "post_message": "POST /threads/{thread_id}/messages",
            },
            "legacy_chat": "POST /chat",
            "ui": {
                "path": "web/",
                "dev_command": "python -m http.server 3000 --directory web",
                "env_hint": "Set NEXT_PUBLIC_API_URL to this API origin (e.g. http://127.0.0.1:8080)",
                "present": web_dir.is_dir(),
            },
            "architecture": "Docs/RAG_Architecture.md",
        }

    @app.get("/health")
    def health() -> dict:
        ensure_warmup_started()
        rag_cfg = load_rag_config()
        version = None
        if rag_cfg.manifest_path.exists():
            version = json.loads(
                rag_cfg.manifest_path.read_text(encoding="utf-8")
            ).get("corpus_version")
        warmup = get_warmup_state()
        return {
            "status": "ok",
            "corpus_version": version,
            "rag": "phase_7",
            "api": "phase_9",
            "retrieval_mode": "sparse" if api_sparse_only() else "hybrid",
            "rag_ready": warmup.get("status") == "ready",
            "warmup": warmup,
        }

    @app.post("/threads", response_model=CreateThreadResponse)
    def create_thread(body: CreateThreadRequest | None = None) -> CreateThreadResponse:
        body = body or CreateThreadRequest()
        record = thread_service.new_thread(session_key=body.session_key)
        return CreateThreadResponse(thread=_thread_summary(record))

    @app.get("/threads", response_model=ThreadListResponse)
    def list_threads(session_key: str | None = None) -> ThreadListResponse:
        records = thread_service.list_threads(session_key=session_key)
        return ThreadListResponse(threads=[_thread_summary(r) for r in records])

    @app.patch("/threads/{thread_id}", response_model=CreateThreadResponse)
    def update_thread(thread_id: str, body: UpdateThreadRequest) -> CreateThreadResponse:
        if body.title is None and body.pinned is None:
            raise HTTPException(status_code=400, detail="Provide title and/or pinned")
        updated = thread_service.update_thread(
            thread_id,
            title=body.title,
            pinned=body.pinned,
        )
        if not updated:
            raise HTTPException(status_code=404, detail="Thread not found")
        return CreateThreadResponse(thread=_thread_summary(updated))

    @app.delete("/threads/{thread_id}")
    def delete_thread(thread_id: str) -> dict:
        deleted = thread_service.delete_thread(thread_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Thread not found")
        return {"ok": True}

    @app.get("/threads/{thread_id}/messages", response_model=MessagesResponse)
    def get_messages(thread_id: str) -> MessagesResponse:
        if not thread_service.store.get_thread(thread_id):
            raise HTTPException(status_code=404, detail="Thread not found")
        messages = thread_service.history(thread_id)
        return MessagesResponse(
            thread_id=thread_id,
            messages=[
                MessageItem(
                    role=m.role,
                    content=m.content,
                    timestamp=m.timestamp,
                    retrieval_debug_id=m.retrieval_debug_id,
                )
                for m in messages
            ],
        )

    @app.post("/threads/{thread_id}/messages", response_model=PostMessageResponse)
    def post_message(thread_id: str, body: PostMessageRequest) -> PostMessageResponse:
        if not thread_service.store.get_thread(thread_id):
            raise HTTPException(status_code=404, detail="Thread not found")
        warmup = get_warmup_state()
        if warmup.get("status") == "loading":
            raise HTTPException(
                status_code=503,
                detail="RAG models are still loading. Retry in 30–60 seconds.",
            )
        if warmup.get("status") == "failed":
            raise HTTPException(
                status_code=503,
                detail=f"RAG warmup failed: {warmup.get('error', 'unknown')}",
            )
        started = time.perf_counter()
        try:
            result, updated = thread_service.post_user_message(
                thread_id,
                body.content,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"RAG failed: {exc}") from exc

        latency_ms = int((time.perf_counter() - started) * 1000)
        assistant = AssistantMessage(
            content=result.answer,
            intent=result.intent,
            source_url=result.source_url,
            content_captured_at=result.content_captured_at,
            corpus_version=result.corpus_version,
            refused=result.refused,
            disclaimer=result.disclaimer,
            education_url=result.education_url,
        )

        debug: DebugInfo | None = None
        if cfg.debug_responses:
            retrieval_debug_id = _latest_assistant_debug_id(thread_id)
            debug = DebugInfo(
                latency_ms=latency_ms,
                chunk_ids=result.chunk_ids,
                intent_matched_by=result.intent_matched_by,
                guardrail_flags=result.guardrail_flags,
                retrieval_debug_id=retrieval_debug_id,
            )

        return PostMessageResponse(
            thread_id=updated.thread_id,
            assistant_message=assistant,
            debug=debug,
        )

    @app.post("/chat", response_model=LegacyChatResponse)
    def legacy_chat(body: LegacyChatRequest) -> LegacyChatResponse:
        """Backward-compatible single-shot chat (prefer POST /threads/{id}/messages)."""
        thread = thread_service.store.get_or_create(
            body.thread_id,
            session_key=body.session_key,
        )
        started = time.perf_counter()
        try:
            result, updated = thread_service.post_user_message(
                thread.thread_id,
                body.query,
                session_key=body.session_key,
            )
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"RAG failed: {exc}") from exc

        _ = int((time.perf_counter() - started) * 1000)
        return LegacyChatResponse(
            answer=result.answer,
            intent=result.intent,
            source_url=result.source_url,
            content_captured_at=result.content_captured_at,
            corpus_version=result.corpus_version,
            chunk_ids=result.chunk_ids if cfg.debug_responses else [],
            refused=result.refused,
            disclaimer=result.disclaimer,
            education_url=result.education_url,
            intent_matched_by=result.intent_matched_by if cfg.debug_responses else None,
            guardrail_flags=result.guardrail_flags if cfg.debug_responses else [],
            thread_id=updated.thread_id,
        )

    @app.post("/admin/reindex")
    def admin_reindex(
        x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
    ) -> None:
        if not cfg.admin_reindex_secret:
            raise HTTPException(
                status_code=503,
                detail="Admin reindex is not configured (set ADMIN_REINDEX_SECRET).",
            )
        if x_admin_secret != cfg.admin_reindex_secret:
            raise HTTPException(status_code=403, detail="Invalid admin secret.")
        raise HTTPException(
            status_code=501,
            detail=(
                "Admin reindex is stubbed in phase 9. "
                "Use `python -m jobs.ingest` locally or the GitHub Actions daily-corpus-refresh workflow."
            ),
        )

    _register_internal_routes(app)
    return app


def _thread_summary(record) -> ThreadSummary:
    return ThreadSummary(
        thread_id=record.thread_id,
        session_key=record.session_key,
        created_at=record.created_at,
        updated_at=record.updated_at,
        title=record.title,
        pinned=record.pinned,
    )


def _latest_assistant_debug_id(thread_id: str) -> str | None:
    for msg in reversed(thread_service.history(thread_id)):
        if msg.role == "assistant" and msg.retrieval_debug_id:
            return msg.retrieval_debug_id
    return None


def _register_internal_routes(app: FastAPI) -> None:
    from pydantic import BaseModel

    class ScrapeResponse(BaseModel):
        scrape_run_id: str
        corpus_changed: bool
        success_count: int
        failed_count: int

    class IngestResponse(BaseModel):
        skipped: bool
        corpus_version: int
        chunk_count: int

    @app.post("/internal/scrape", response_model=ScrapeResponse)
    def scrape_all() -> ScrapeResponse:
        from phases.p0_scrape import run_scrape

        run = run_scrape()
        if run.failed_count > 0 and run.success_count == 0:
            raise HTTPException(status_code=500, detail="All schemes failed to scrape")
        return ScrapeResponse(
            scrape_run_id=run.scrape_run_id,
            corpus_changed=run.corpus_changed,
            success_count=run.success_count,
            failed_count=run.failed_count,
        )

    @app.post("/internal/scrape/{scheme_id}", response_model=ScrapeResponse)
    def scrape_one(scheme_id: str) -> ScrapeResponse:
        run = run_scrape(scheme_ids=[scheme_id])
        if run.failed_count:
            raise HTTPException(status_code=500, detail=f"Scrape failed for {scheme_id}")
        return ScrapeResponse(
            scrape_run_id=run.scrape_run_id,
            corpus_changed=run.corpus_changed,
            success_count=run.success_count,
            failed_count=run.failed_count,
        )

    @app.post("/internal/ingest", response_model=IngestResponse)
    def ingest_all(force: bool = False, force_reembed: bool = False) -> IngestResponse:
        from pipeline.ingest import run_ingest

        result = run_ingest(force=force, force_reembed=force_reembed)
        return IngestResponse(
            skipped=result.skipped,
            corpus_version=result.corpus_version,
            chunk_count=result.chunk_count,
        )


app = create_app()
