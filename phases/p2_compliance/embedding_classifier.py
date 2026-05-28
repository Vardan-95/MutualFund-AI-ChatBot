from __future__ import annotations

import numpy as np

from phases.p2_compliance.config import ComplianceConfig
from phases.p2_compliance.intents import INTENT_ADVISORY, INTENT_COMPARISON


def _cosine(a: list[float], b: list[float]) -> float:
    va = np.array(a, dtype=np.float32)
    vb = np.array(b, dtype=np.float32)
    na, nb = np.linalg.norm(va), np.linalg.norm(vb)
    if na == 0 or nb == 0:
        return 0.0
    return float(np.dot(va, vb) / (na * nb))


def classify_by_exemplars(
    query: str,
    cfg: ComplianceConfig,
) -> tuple[str | None, float]:
    """Return (INTENT_ADVISORY|INTENT_COMPARISON, score) if similar to exemplars."""
    try:
        from pipeline.config import load_embedding_config
        from pipeline.embedder import EmbeddingService

        embed_cfg = load_embedding_config()
        service = EmbeddingService(embed_cfg)
        q_vec = service.embed_batch([query])[0]

        for label, texts, threshold in (
            (INTENT_ADVISORY, cfg.advisory_exemplars, cfg.advisory_similarity_threshold),
            (INTENT_COMPARISON, cfg.comparison_exemplars, cfg.comparison_similarity_threshold),
        ):
            for text in texts:
                ex_vec = service.embed_batch([text])[0]
                score = _cosine(q_vec, ex_vec)
                if score >= threshold:
                    return label, score
    except Exception:
        pass
    return None, 0.0
