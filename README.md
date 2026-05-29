# Mutual Fund FAQ Assistant

Facts-only RAG assistant for HDFC mutual fund schemes on Groww. See [Docs/ProblemStatement.md](Docs/ProblemStatement.md) and [Docs/RAG_Architecture.md](Docs/RAG_Architecture.md).

## Project layout

```
config/                 # sources.yaml, scraper.yaml
phases/
  p0_scrape/            # Groww scraping service (§4.2)
  p0b_scheduler/        # GitHub Actions output helpers (§4.8)
  p1_rag/               # Ingestion indexes (§4.3–4.4) — see pipeline/
  p2_compliance/ … p4_ops/
pipeline/               # normalize, chunk, embed, BM25
jobs/
  scrape/               # python -m jobs.scrape
  ingest/               # python -m jobs.ingest
api/                    # POST /internal/scrape, /internal/ingest
data/
  corpus/               # Scraped Markdown (+ Key fund metrics section)
  facts/                # Structured NAV, SIP, AUM, expense ratio, rating (JSON)
  raw/                  # HTML archives
  index/                # chunks.jsonl, BM25, manifests (vectors in Chroma Cloud)
.github/workflows/
  daily-corpus-refresh.yml
```

## Setup (scraping)

```bash
cd "e:\AI Projects\Mutual fund"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-scrape.txt
```

## Environment variables (`.env`)

Copy `.env.example` to `.env` (already created if missing) and fill in:

| Variable | Used for |
|----------|----------|
| `CHROMA_API_KEY` | Python ingest / RAG (`CloudClient`) |
| `CHROMA_TENANT` | Chroma Cloud tenant ID |
| `CHROMA_DATABASE` | Database name |
| `CHROMA_CLI_API_KEY` | `chroma login` in the terminal (can match `CHROMA_API_KEY`) |
| `GROQ_API_KEY` | LLM answers (P1); from [console.groq.com](https://console.groq.com/) |
| `GROQ_MODEL` | Optional; default `llama-3.3-70b-versatile` |

```powershell
copy .env.example .env
# Edit .env in your editor, then:
pip install -r requirements-ingest.txt
.\scripts\chroma-login.ps1
```

Dense vectors are stored on [Chroma Cloud](https://www.trychroma.com/), not under `data/index/chroma/`.

## Run pipeline locally

```bash
set PYTHONPATH=.
# Ensure .env has CHROMA_* before ingest

# §4.2 Scrape all Groww pages
python -m jobs.scrape

# §4.3–4.4 Ingest: validate, chunk, embed → Chroma Cloud, BM25
python -m jobs.ingest --force

# P1 — Ask a question (CLI)
python -m pipeline.rag "What is the minimum SIP for HDFC Large Cap Fund Direct Growth?"

# API: scrape, ingest, chat
uvicorn api.main:app --reload --port 8080
# POST http://localhost:8080/chat  {"query": "What is the expense ratio for HDFC Mid Cap?"}
```

Set `GROQ_API_KEY` in `.env` for LLM answers via [Groq](https://console.groq.com/) (default model in `config/rag.yaml`). Optional `OPENAI_API_KEY` as fallback.

Outputs:

- `data/corpus/*.md` — scheme pages with YAML front matter + **Key fund metrics** table
- `data/facts/scheme_facts.json` — structured NAV, min SIP, AUM, expense ratio, rating ([details](Docs/Fund_Facts_Storage.md))
- `data/index/chunks.jsonl` — retrieval chunks
- **Chroma Cloud** collection `mutual_fund_chunks` — dense vector index
- `data/index/bm25/` — sparse index (local)
- `data/index/ingestion_manifest.json` — scrape + ingest audit trail
- `data/raw/{scheme_id}/{date}/page.html` — optional HTML archive

## Scheduler (GitHub Actions)

Workflow: `.github/workflows/daily-corpus-refresh.yml`

- **Schedule**: 9:15 AM IST daily (`45 3 * * *` UTC)
- **Pipeline**: scrape → chunk → embed to **Chroma Cloud** → BM25 → **commit & push to `main`** (ingest always runs on schedule)
- **Production**: push to `main` triggers **Render auto-deploy** with fresh `data/corpus` + `data/index/bm25` (enable Auto-Deploy on Render for `main`)
- **Secrets** (repo settings): `CHROMA_API_KEY`, `CHROMA_TENANT`, `CHROMA_DATABASE` (+ optional `CHROMA_HOST`, `RENDER_DEPLOY_HOOK`)
- **Manual**: Actions → Daily corpus refresh → enable **force_reindex** to re-run ingest without new scrape data

## Disclaimer

Facts-only. No investment advice.
