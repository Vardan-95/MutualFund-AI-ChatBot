# Phase P0 — Scraping Service

Implements [RAG Architecture §4.2](../../Docs/RAG_Architecture.md).

## Modules

| Module | Role |
|--------|------|
| `fetcher.py` | HTTP GET with allowlist, retries, politeness |
| `extractor.py` | HTML → Markdown (trafilatura + markdownify) |
| `writer.py` | YAML front matter + corpus files |
| `manifest.py` | `data/index/ingestion_manifest.json` |
| `facts_extractor.py` | NAV, min SIP, AUM, expense ratio, rating → structured JSON |
| `facts_store.py` | Writes `data/facts/scheme_facts.json` |
| `service.py` | Orchestrates full scrape run |

Structured storage: [Fund_Facts_Storage.md](../../Docs/Fund_Facts_Storage.md).

## Run locally

```bash
pip install -r requirements-scrape.txt
python -m jobs.scrape
python -m jobs.scrape --scheme hdfc_large_cap_direct_growth
```
