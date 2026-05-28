# Phase P3 — UI & Chat API

Planned: production UI (Next.js) with multi-thread chat ([RAG Architecture §3.1, §6, §7](../../Docs/RAG_Architecture.md)).

## Current test UI

A basic static test UI is available under `web/` for manual API testing.

Run:

```bash
set PYTHONPATH=.
python -m runtime.phase_9_api
python -m http.server 3000 --directory web
```

Open: `http://127.0.0.1:3000`
