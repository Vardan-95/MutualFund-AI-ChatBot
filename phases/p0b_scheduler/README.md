# Phase P0b — Scheduler (GitHub Actions)

Implements [RAG Architecture §4.8](../../Docs/RAG_Architecture.md).

**Workflow:** `.github/workflows/daily-corpus-refresh.yml`

## Schedule

| Setting | Value |
|---------|--------|
| Local time | **9:15 AM IST** daily |
| Cron (UTC) | `45 3 * * *` |

## Pipeline order (every scheduled run)

```text
1. Scrape     python -m jobs.scrape
              → data/corpus/*.md from Groww URLs (sources.yaml)

2. Ingest     python -m jobs.ingest --force --force-reembed
              → chunk (chunks.jsonl)
              → embed (BGE) → upsert Chroma Cloud (mutual_fund_chunks)
              → BM25 index (data/index/bm25/)
              → validate + manifests
```

On the **daily schedule**, ingest **always** runs after a successful scrape (even if `corpus_changed` is false), so Chroma Cloud and local indexes stay in sync with the latest scrape.

On **manual** `workflow_dispatch`, ingest runs only if the scrape changed content or you check **force_reindex**.

## 3. Push to `main` → Render auto-deploy

After ingest, job **`push-to-main`** commits:

- `data/corpus/`, `data/facts/`
- `data/index/chunks.jsonl`, `data/index/bm25/`, manifests

and pushes to **`main`**. If your Render service has **Auto-Deploy** enabled for `main`, Render rebuilds with the new BM25/corpus (production chat uses sparse/BM25 on the free tier).

Optional: set GitHub secret **`RENDER_DEPLOY_HOOK`** (from Render → Service → Deploy Hook) to force a deploy even when Git auto-deploy is slow.

## Required GitHub secrets

| Secret | Purpose |
|--------|---------|
| `CHROMA_API_KEY` | Chroma Cloud write for embed job |
| `CHROMA_TENANT` | Tenant ID |
| `CHROMA_DATABASE` | Database name |
| `CHROMA_HOST` | Optional (non-default region) |
| `RENDER_DEPLOY_HOOK` | Optional Render deploy URL after push |

## GitHub repo settings (one-time)

- **Settings → Actions → General → Workflow permissions**: **Read and write**
- If `main` is branch-protected: allow **github-actions[bot]** to push, or use a PAT in a custom secret

## Render settings (one-time)

- Service linked to this repo, branch **`main`**
- **Auto-Deploy**: **On**

## Manual run

GitHub → Actions → **Daily corpus refresh** → Run workflow

- **force_reindex**: chunk + embed + Chroma even when scrape hash unchanged
