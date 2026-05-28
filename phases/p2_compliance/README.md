# Phase P2 — Compliance

Intent routing, refusal, and output guardrails ([RAG Architecture §3.3.1](../../Docs/RAG_Architecture.md), [§3.3.4](../../Docs/RAG_Architecture.md)).

## Implemented

| Module | Path |
|--------|------|
| Config | `config/compliance.yaml` |
| Intent labels | `intents.py` |
| Scheme scope / detection | `scheme_scope.py` |
| Rule + embedding router | `intent_router.py`, `embedding_classifier.py` |
| Refusal templates | `refusal.py` |
| Output guardrails | `guardrails.py` |

`pipeline/rag/intent.py` and `pipeline/rag/guardrails.py` re-export this package for P1 orchestrator.

## Intent flow

1. **Rules** — advisory / comparison patterns → refuse (no retrieval)
2. **BGE exemplars** — similarity to labeled refusal phrases in `compliance.yaml`
3. **Scope** — other AMCs, unknown schemes → `OUT_OF_SCOPE`
4. **Allow** — `FACTUAL_LOOKUP`, `PROCESS_HOWTO`, `PERFORMANCE_REQUEST` → RAG

## Guardrails (post-generation)

- ≤3 sentences, no tables
- Advisory / comparison language → refusal
- PII redaction (email, phone, PAN patterns)
- Citation URL must be in corpus allowlist
- Performance answers: block unsourced return figures

## Test

```bash
set PYTHONPATH=.
python -m pipeline.rag "Should I invest in HDFC Mid Cap?"
python -m pipeline.rag "Compare HDFC Mid Cap vs Large Cap"
python -m pipeline.rag "What is the expense ratio for HDFC ELSS?"
```
