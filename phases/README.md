# Implementation Phases

Code is organized by implementation phase (see `Docs/RAG_Architecture.md` §15).

| Folder | Architecture | Status |
|--------|--------------|--------|
| [p0_scrape](./p0_scrape/) | §4.2 Groww scraping service | Implemented |
| [p0b_scheduler](./p0b_scheduler/) | §4.8 GitHub Actions scheduler helpers | Implemented |
| [p1_rag](./p1_rag/) | §3 RAG runtime (`runtime/phase_5–7`, `pipeline/rag/`) | Implemented |
| [p2_compliance](./p2_compliance/) | §3.3.1 Refusal & guardrails | Implemented |
| [p3_ui](./p3_ui/) | §3.1, §7 Next.js UI (`web/`) | Planned |
| [p4_ops](./p4_ops/) | §10 Observability, golden eval | Planned |

**Runtime modules** (query-time): `runtime/phase_5_retrieval` … `runtime/phase_9_api` — see [RAG_Architecture.md §15](../Docs/RAG_Architecture.md).

Shared utilities: [common](./common/).

CLI entrypoints: [../jobs/](../jobs/).
