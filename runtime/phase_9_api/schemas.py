from __future__ import annotations

from pydantic import BaseModel, Field


class CreateThreadRequest(BaseModel):
    session_key: str | None = None


class ThreadSummary(BaseModel):
    thread_id: str
    session_key: str | None = None
    created_at: str
    updated_at: str
    title: str | None = None
    pinned: bool = False


class CreateThreadResponse(BaseModel):
    thread: ThreadSummary


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary]


class UpdateThreadRequest(BaseModel):
    title: str | None = Field(default=None, max_length=80)
    pinned: bool | None = None


class MessageItem(BaseModel):
    role: str
    content: str
    timestamp: str
    retrieval_debug_id: str | None = None


class MessagesResponse(BaseModel):
    thread_id: str
    messages: list[MessageItem]


class PostMessageRequest(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)


class AssistantMessage(BaseModel):
    content: str
    intent: str
    source_url: str | None = None
    content_captured_at: str | None = None
    corpus_version: int | None = None
    refused: bool = False
    disclaimer: str = ""
    education_url: str | None = None


class DebugInfo(BaseModel):
    latency_ms: int
    chunk_ids: list[str] = []
    intent_matched_by: str | None = None
    guardrail_flags: list[str] = []
    retrieval_debug_id: str | None = None


class PostMessageResponse(BaseModel):
    thread_id: str
    assistant_message: AssistantMessage
    debug: DebugInfo | None = None


class LegacyChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    thread_id: str | None = None
    session_key: str | None = None


class LegacyChatResponse(BaseModel):
    answer: str
    intent: str
    source_url: str | None
    content_captured_at: str | None
    corpus_version: int | None
    chunk_ids: list[str] = []
    refused: bool = False
    disclaimer: str = ""
    education_url: str | None = None
    intent_matched_by: str | None = None
    guardrail_flags: list[str] = []
    thread_id: str
