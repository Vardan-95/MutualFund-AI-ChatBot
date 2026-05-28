from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from phases.common.config_loader import load_yaml
from phases.common.paths import CONFIG_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class RetrievalConfig:
    dense_top_k: int
    sparse_top_k: int
    rerank_top_k: int
    similarity_threshold: float
    rrf_k: int
    dense_weight: float
    sparse_weight: float
    scheme_filter_min_confidence: float
    merge_by_source_url: bool
    use_cross_encoder: bool
    cross_encoder_model: str
    cross_encoder_top_n: int
    detect_numeric_conflicts: bool
    chunks_path: Path
    bm25_dir: Path
    collection_name: str


def load_retrieval_config(path: Path | None = None) -> RetrievalConfig:
    data = load_yaml(path or CONFIG_DIR / "rag.yaml")
    retrieval = data.get("retrieval", {})
    ingest = load_yaml(CONFIG_DIR / "ingest.yaml")
    embed = load_yaml(CONFIG_DIR / "embedding.yaml")

    return RetrievalConfig(
        dense_top_k=int(retrieval.get("dense_top_k", 20)),
        sparse_top_k=int(retrieval.get("sparse_top_k", 20)),
        rerank_top_k=int(retrieval.get("rerank_top_k", 5)),
        similarity_threshold=float(retrieval.get("similarity_threshold", 0.72)),
        rrf_k=int(retrieval.get("rrf_k", 60)),
        dense_weight=float(retrieval.get("dense_weight", 0.7)),
        sparse_weight=float(retrieval.get("sparse_weight", 0.3)),
        scheme_filter_min_confidence=float(
            retrieval.get("scheme_filter_min_confidence", 0.85)
        ),
        merge_by_source_url=bool(retrieval.get("merge_by_source_url", True)),
        use_cross_encoder=bool(retrieval.get("use_cross_encoder", False)),
        cross_encoder_model=str(
            retrieval.get(
                "cross_encoder_model",
                "cross-encoder/ms-marco-MiniLM-L-6-v2",
            )
        ),
        cross_encoder_top_n=int(retrieval.get("cross_encoder_top_n", 20)),
        detect_numeric_conflicts=bool(retrieval.get("detect_numeric_conflicts", True)),
        chunks_path=PROJECT_ROOT / ingest.get("chunks_path", "data/index/chunks.jsonl"),
        bm25_dir=PROJECT_ROOT / ingest.get("bm25_dir", "data/index/bm25"),
        collection_name=str(embed.get("collection_name", "mutual_fund_chunks")),
    )
