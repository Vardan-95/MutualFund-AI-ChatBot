# Phase 7 — Refusal & safety

- **Router:** rules + BGE exemplars (§7.1); blocks advisory/comparison before retrieval
- **Validation:** ≤3 sentences, forbidden phrases, citation allowlist (§7.2)
- **PII:** redact email/phone/PAN patterns (§7.3)
- **Orchestration:** `answer()` runs phase 5 → 6 → validation

```bash
set PYTHONPATH=.
python -m runtime.phase_7_safety --route-only "Which fund is better?"
python -m runtime.phase_7_safety "What is the expense ratio for HDFC ELSS?"
```

Override education URL: `EDUCATIONAL_URL` in `.env`.
