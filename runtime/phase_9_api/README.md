# Phase 9 — Application & API

FastAPI + uvicorn entry point for the mutual fund FAQ assistant.

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Service pointers (docs, UI, threads API) |
| GET | `/health` | Liveness + corpus version |
| POST | `/threads` | Create thread |
| GET | `/threads` | List threads |
| GET | `/threads/{id}/messages` | Message history |
| POST | `/threads/{id}/messages` | User message → RAG → assistant reply |
| POST | `/chat` | Legacy alias (P1) |
| POST | `/admin/reindex` | Protected stub (501) |

## Run

```bash
set PYTHONPATH=.
python -m runtime.phase_9_api
# or: uvicorn runtime.phase_9_api.app:app --host 127.0.0.1 --port 8080
```

## Environment

- `PORT`, `API_HOST` — bind address
- `RUNTIME_API_DEBUG=1` — include `debug` on `POST /threads/{id}/messages` (latency, chunk IDs)
- `ADMIN_REINDEX_SECRET` — required header `X-Admin-Secret` for `/admin/reindex`
- `API_CORS_ORIGINS` — comma-separated (default `http://localhost:3000` for Next.js)
- `NEXT_PUBLIC_API_URL` — set in `web/` when UI is added (see GET `/`)

Production: leave `RUNTIME_API_DEBUG` unset so chunk IDs are not returned on `/chat`.
