from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from phases.common.config_loader import load_yaml
from phases.common.paths import CONFIG_DIR, PROJECT_ROOT


@dataclass(frozen=True)
class RagConfig:
    dense_top_k: int
    sparse_top_k: int
    rerank_top_k: int
    similarity_threshold: float
    rrf_k: int
    dense_weight: float
    sparse_weight: float
    max_sentences: int
    temperature: float
    max_tokens: int
    llm_provider: str
    llm_model: str
    llm_base_url: str
    refusal_education_url: str
    allowed_citation_domains: list[str]
    disclaimer: str
    chunks_path: Path
    bm25_dir: Path
    manifest_path: Path


def _resolve_llm_provider(generation: dict) -> str:
    env = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if env in ("groq", "openai"):
        return env
    return str(generation.get("provider", "groq")).lower()


def _resolve_llm_model(generation: dict) -> str:
    provider = _resolve_llm_provider(generation)
    if provider == "groq":
        return os.environ.get(
            "GROQ_MODEL",
            str(generation.get("model", "llama-3.3-70b-versatile")),
        )
    return os.environ.get("OPENAI_MODEL", str(generation.get("model", "gpt-4o-mini")))


def _resolve_llm_base_url(generation: dict) -> str:
    provider = _resolve_llm_provider(generation)
    if provider == "groq":
        return os.environ.get(
            "GROQ_BASE_URL",
            str(generation.get("groq_base_url", "https://api.groq.com/openai/v1")),
        )
    return os.environ.get("OPENAI_BASE_URL", str(generation.get("openai_base_url", "")))


def load_rag_config(path: Path | None = None) -> RagConfig:
    data = load_yaml(path or CONFIG_DIR / "rag.yaml")
    retrieval = data.get("retrieval", {})
    generation = data.get("generation", {})
    refusal = data.get("refusal", {})
    guardrails = data.get("guardrails", {})
    ingest = load_yaml(CONFIG_DIR / "ingest.yaml")

    return RagConfig(
        dense_top_k=int(retrieval.get("dense_top_k", 20)),
        sparse_top_k=int(retrieval.get("sparse_top_k", 20)),
        rerank_top_k=int(retrieval.get("rerank_top_k", 5)),
        similarity_threshold=float(retrieval.get("similarity_threshold", 0.72)),
        rrf_k=int(retrieval.get("rrf_k", 60)),
        dense_weight=float(retrieval.get("dense_weight", 0.7)),
        sparse_weight=float(retrieval.get("sparse_weight", 0.3)),
        max_sentences=int(generation.get("max_sentences", 3)),
        temperature=float(generation.get("temperature", 0.1)),
        max_tokens=int(generation.get("max_tokens", 180)),
        llm_provider=_resolve_llm_provider(generation),
        llm_model=_resolve_llm_model(generation),
        llm_base_url=_resolve_llm_base_url(generation),
        refusal_education_url=str(
            refusal.get(
                "default_education_url",
                "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionToMF",
            )
        ),
        allowed_citation_domains=list(guardrails.get("allowed_citation_domains", ["groww.in"])),
        disclaimer=str(data.get("disclaimer", "")).strip(),
        chunks_path=PROJECT_ROOT / ingest.get("chunks_path", "data/index/chunks.jsonl"),
        bm25_dir=PROJECT_ROOT / ingest.get("bm25_dir", "data/index/bm25"),
        manifest_path=PROJECT_ROOT / ingest.get("manifest_path", "data/index/ingestion_manifest.json"),
    )
