from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from phases.common.config_loader import load_sources_config
from phases.common.paths import CONFIG_DIR, PROJECT_ROOT
from phases.common.config_loader import load_yaml


@dataclass(frozen=True)
class ChunkingConfig:
    token_encoding: str
    min_chunk_tokens: int
    target_chunk_tokens: int
    max_section_tokens: int
    hard_max_tokens: int
    sentence_overlap_tokens: int
    merge_short_sections: bool
    dense_fact_chunk_enabled: bool
    canonical_sections: list[str]


@dataclass(frozen=True)
class EmbeddingConfig:
    provider: str
    model: str
    dimensions: int
    batch_size: int
    max_retries: int
    retry_backoff_seconds: float
    normalize_vectors: bool
    prefix_scheme_name: bool
    cache_dir: str
    collection_name: str
    chroma_mode: str
    chroma_persist_dir: str
    chroma_cloud_host: str


@dataclass(frozen=True)
class IngestConfig:
    corpus_dir: Path
    index_dir: Path
    manifest_path: Path
    chunks_path: Path
    bm25_dir: Path
    embeddings_manifest_path: Path
    require_all_schemes: bool
    keep_last_good_index: bool
    snapshot_dir: Path


def load_chunking_config(path: Path | None = None) -> ChunkingConfig:
    data = load_yaml(path or CONFIG_DIR / "chunking.yaml")
    return ChunkingConfig(
        token_encoding=str(data.get("token_encoding", "cl100k_base")),
        min_chunk_tokens=int(data.get("min_chunk_tokens", 80)),
        target_chunk_tokens=int(data.get("target_chunk_tokens", 300)),
        max_section_tokens=int(data.get("max_section_tokens", 450)),
        hard_max_tokens=int(data.get("hard_max_tokens", 512)),
        sentence_overlap_tokens=int(data.get("sentence_overlap_tokens", 50)),
        merge_short_sections=bool(data.get("merge_short_sections", True)),
        dense_fact_chunk_enabled=bool(data.get("dense_fact_chunk_enabled", True)),
        canonical_sections=list(data.get("canonical_sections", ["other"])),
    )


def load_embedding_config(path: Path | None = None) -> EmbeddingConfig:
    import os

    data = load_yaml(path or CONFIG_DIR / "embedding.yaml")
    provider = os.environ.get("EMBEDDING_PROVIDER", str(data.get("provider", "local")))
    model = os.environ.get(
        "EMBEDDING_MODEL",
        str(data.get("model", "BAAI/bge-small-en-v1.5")),
    )
    dimensions = int(os.environ.get("EMBEDDING_DIMENSIONS", data.get("dimensions", 384)))
    chroma_mode = os.environ.get("CHROMA_MODE", str(data.get("chroma_mode", "cloud"))).lower()
    if chroma_mode not in ("cloud", "local"):
        chroma_mode = "cloud"
    return EmbeddingConfig(
        provider=provider,
        model=model,
        dimensions=dimensions,
        batch_size=int(data.get("batch_size", 32)),
        max_retries=int(data.get("max_retries", 3)),
        retry_backoff_seconds=float(data.get("retry_backoff_seconds", 2)),
        normalize_vectors=bool(data.get("normalize_vectors", True)),
        prefix_scheme_name=bool(data.get("prefix_scheme_name", False)),
        cache_dir=str(data.get("cache_dir", "data/index/embed_cache")),
        collection_name=str(data.get("collection_name", "mutual_fund_chunks")),
        chroma_mode=chroma_mode,
        chroma_persist_dir=str(data.get("chroma_persist_dir", "data/index/chroma")),
        chroma_cloud_host=str(
            os.environ.get("CHROMA_HOST", data.get("chroma_cloud_host", ""))
        ),
    )


def load_ingest_config(path: Path | None = None) -> IngestConfig:
    data = load_yaml(path or CONFIG_DIR / "ingest.yaml")
    return IngestConfig(
        corpus_dir=PROJECT_ROOT / data.get("corpus_dir", "data/corpus"),
        index_dir=PROJECT_ROOT / data.get("index_dir", "data/index"),
        manifest_path=PROJECT_ROOT / data.get("manifest_path", "data/index/ingestion_manifest.json"),
        chunks_path=PROJECT_ROOT / data.get("chunks_path", "data/index/chunks.jsonl"),
        bm25_dir=PROJECT_ROOT / data.get("bm25_dir", "data/index/bm25"),
        embeddings_manifest_path=PROJECT_ROOT
        / data.get("embeddings_manifest_path", "data/index/embeddings_manifest.json"),
        require_all_schemes=bool(data.get("require_all_schemes", True)),
        keep_last_good_index=bool(data.get("keep_last_good_index", True)),
        snapshot_dir=PROJECT_ROOT / data.get("snapshot_dir", "data/index/snapshots"),
    )


def allowed_source_urls() -> set[str]:
    return {s.source_url for s in load_sources_config().sources}
