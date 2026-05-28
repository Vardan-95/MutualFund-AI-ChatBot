# Phase P1 — RAG query runtime

## Implemented

| Component | Path |
|-----------|------|
| Config | `config/rag.yaml` |
| Intent router (rules) | `phases/p2_compliance/` + `runtime/phase_7_safety/router.py` |
| Hybrid retrieval (phase 5) | `runtime/phase_5_retrieval/` |
| Generation (phase 6) | `runtime/phase_6_generation/` |
| Safety / orchestration (phase 7) | `runtime/phase_7_safety/` |
| Multi-thread chat (phase 8) | `runtime/phase_8_threads/` (SQLite) |
| Answer polish (no tables, ≤3 sentences) | `pipeline/rag/answer_format.py` |
| Orchestrator | `pipeline/rag/orchestrator.py` |

## CLI

```bash
set PYTHONPATH=.
python -m pipeline.rag "What is the expense ratio of HDFC Large Cap Fund Direct Growth?"
python -m pipeline.rag "What is the minimum SIP?" --json
python -m runtime.phase_5_retrieval "What is the exit load for HDFC ELSS?" --json
python -m runtime.phase_6_generation "What is the minimum SIP for HDFC Large Cap?"
python -m runtime.phase_7_safety "Should I invest in HDFC Mid Cap?" --route-only
python -m runtime.phase_7_safety "What is the expense ratio for HDFC ELSS?"
python -m runtime.phase_8_threads new-thread
python -m runtime.phase_8_threads say <thread-id> What is the exit load?
```

**Footer policy:** `generation.footer_policy: cited_source` in `config/rag.yaml` — the response footer uses the **cited chunk’s** `content_captured_at` only (not the max across all retrieved chunks).

## API

```bash
uvicorn api.main:app --reload --port 8080
# or phase 9 entry:
python -m runtime.phase_9_api
```

```http
POST /threads
POST /threads/{thread_id}/messages
{"content": "What is the exit load for HDFC ELSS?"}
GET /threads/{thread_id}/messages
GET /health
```

Legacy: `POST /chat` with `{"query": "...", "thread_id": null}`.

Set `RUNTIME_API_DEBUG=1` for chunk IDs and latency on post-message (dev only).

**LLM (Groq):** set `GROQ_API_KEY` in `.env` ([console.groq.com](https://console.groq.com/)). Default model: `llama-3.3-70b-versatile` (`config/rag.yaml`). If no API key, extractive fallback from top chunk.

Optional: `OPENAI_API_KEY` instead (Groq is used when both are set).

## Prerequisites

- `python -m jobs.ingest` completed (Chroma Cloud + `chunks.jsonl` + BM25)
- `.env` with `CHROMA_*` credentials
- `.env` with `GROQ_API_KEY` for LLM-generated answers
