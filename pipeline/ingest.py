from __future__ import annotations

import json
from dataclasses import dataclass

from pipeline.bm25_index import build_bm25_index
from pipeline.chunk_validator import validate_chunks
from pipeline.chunker import ChunkRecord, chunk_document
from pipeline.config import (
    load_chunking_config,
    load_embedding_config,
    load_ingest_config,
)
from pipeline.corpus_loader import CorpusValidationError, load_corpus_documents
from pipeline.embedder import EmbeddingService
from pipeline.vector_store import write_vectors
from pipeline.normalize import normalize_document
from pipeline.versioning import (
    load_manifest,
    record_ingest_run,
    restore_snapshot,
    save_manifest,
    snapshot_index,
)


@dataclass
class IngestResult:
    skipped: bool
    corpus_version: int
    chunk_count: int
    schemes: int
    skipped_embed_cache: int


class IngestPipeline:
    def __init__(self) -> None:
        self.ingest_cfg = load_ingest_config()
        self.chunk_cfg = load_chunking_config()
        self.embed_cfg = load_embedding_config()

    def run(
        self,
        *,
        step: str | None = None,
        force_reembed: bool = False,
        force: bool = False,
    ) -> IngestResult:
        manifest = load_manifest(self.ingest_cfg.manifest_path)
        prev_version = int(manifest.get("corpus_version", 0))
        last_scrape = manifest.get("last_scrape_run", {})

        if not force and last_scrape and not last_scrape.get("corpus_changed", True):
            last_ingest = manifest.get("last_ingest_run", {})
            return IngestResult(
                skipped=True,
                corpus_version=prev_version,
                chunk_count=int(last_ingest.get("chunk_count", 0)),
                schemes=len(manifest.get("schemes", {})),
                skipped_embed_cache=0,
            )

        run_all = step is None or step == "all"
        steps = {"chunk", "embed", "bm25", "validate"} if run_all else {step or "chunk"}

        chunks: list[ChunkRecord] = []
        new_version = prev_version + 1

        if "chunk" in steps or run_all:
            documents = load_corpus_documents(self.ingest_cfg.corpus_dir)
            if self.ingest_cfg.require_all_schemes and len(documents) < 5:
                raise CorpusValidationError(
                    f"Expected 5 corpus files, found {len(documents)}"
                )
            for doc in documents:
                norm = normalize_document(doc, self.chunk_cfg)
                chunks.extend(chunk_document(norm, self.chunk_cfg, new_version))
            chunks = validate_chunks(chunks, self.chunk_cfg)
            self._write_chunks_jsonl(chunks)
        else:
            chunks = self._read_chunks_jsonl()
            if not chunks:
                raise CorpusValidationError("No chunks.jsonl; run --step chunk first")

        local_chroma = self.embed_cfg.chroma_mode == "local"
        if self.ingest_cfg.keep_last_good_index and prev_version > 0:
            snapshot_index(
                self.ingest_cfg.index_dir,
                self.ingest_cfg.snapshot_dir,
                prev_version,
                include_local_chroma=local_chroma,
            )

        skipped_cache = 0
        try:
            if "embed" in steps or run_all:
                embedder = EmbeddingService(self.embed_cfg)
                ids, vectors, skipped_cache = embedder.embed_chunks(
                    chunks, force=force_reembed
                )
                backend, count = write_vectors(chunks, ids, vectors, self.embed_cfg)
                self._write_embeddings_manifest(count, new_version, backend)

            if "bm25" in steps or run_all:
                build_bm25_index(chunks, self.ingest_cfg.bm25_dir)

            if "validate" in steps or run_all:
                validate_chunks(chunks, self.chunk_cfg)

        except Exception:
            if self.ingest_cfg.keep_last_good_index and prev_version > 0:
                restore_snapshot(
                    self.ingest_cfg.index_dir,
                    self.ingest_cfg.snapshot_dir,
                    prev_version,
                    include_local_chroma=local_chroma,
                )
            raise

        manifest = record_ingest_run(
            manifest,
            chunk_count=len(chunks),
            corpus_version=new_version,
            embedding_model=self.embed_cfg.model,
            skipped_cache=skipped_cache,
        )
        save_manifest(self.ingest_cfg.manifest_path, manifest)

        return IngestResult(
            skipped=False,
            corpus_version=new_version,
            chunk_count=len(chunks),
            schemes=len({c.metadata["scheme_id"] for c in chunks}),
            skipped_embed_cache=skipped_cache,
        )

    def _write_chunks_jsonl(self, chunks: list[ChunkRecord]) -> None:
        path = self.ingest_cfg.chunks_path
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            for ch in chunks:
                row = {
                    "chunk_id": ch.chunk_id,
                    "text": ch.text,
                    "token_count": ch.token_count,
                    "metadata": ch.metadata,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def _read_chunks_jsonl(self) -> list[ChunkRecord]:
        chunks: list[ChunkRecord] = []
        path = self.ingest_cfg.chunks_path
        if not path.exists():
            return chunks
        with path.open(encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                chunks.append(
                    ChunkRecord(
                        chunk_id=row["chunk_id"],
                        text=row["text"],
                        token_count=row["token_count"],
                        metadata=row["metadata"],
                    )
                )
        return chunks

    def _write_embeddings_manifest(
        self, count: int, corpus_version: int, backend: str = "chroma_cloud"
    ) -> None:
        data = {
            "embedding_model": self.embed_cfg.model,
            "embedding_provider": self.embed_cfg.provider,
            "embedding_dimensions": self.embed_cfg.dimensions,
            "vector_store": backend,
            "collection_name": self.embed_cfg.collection_name,
            "chunk_count": count,
            "corpus_version": corpus_version,
        }
        self.ingest_cfg.embeddings_manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.ingest_cfg.embeddings_manifest_path.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8",
        )


def run_ingest(**kwargs) -> IngestResult:
    return IngestPipeline().run(**kwargs)
