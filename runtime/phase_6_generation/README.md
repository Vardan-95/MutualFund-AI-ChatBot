# Phase 6 — Generation layer

- **Context:** `Source URL:` headers per chunk (§6.1)
- **LLM:** Groq/OpenAI via `GROQ_API_KEY`
- **Validation:** delegated to phase 7 after generation

```bash
set PYTHONPATH=.
python -m runtime.phase_6_generation "What is the minimum SIP for HDFC Large Cap?"
```

Footer policy: see `generation.footer_policy` in `config/rag.yaml` (`cited_source` = date on the cited chunk only).
