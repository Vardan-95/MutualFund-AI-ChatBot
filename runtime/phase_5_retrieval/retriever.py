from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache

from phases.common.runtime_mode import api_sparse_only
from pipeline.bm25_index import load_bm25_index, search_bm25
from pipeline.config import load_embedding_config
from pipeline.rag.chunk_index import ChunkIndex
from runtime.phase_5_retrieval.models import RetrievedChunk
from runtime.phase_5_retrieval.config import RetrievalConfig, load_retrieval_config
from runtime.phase_5_retrieval.conflicts import (
    chunks_contain_unsafe_numeric_spread,
    detect_numeric_conflict,
)
from runtime.phase_5_retrieval.merge import merge_chunks_by_source_url
from runtime.phase_5_retrieval.preprocess import (
    PreprocessedQuery,
    preprocess_query,
    query_terms_for_match,
)

@dataclass(frozen=True)
class RetrievalResult:
    chunks: list[RetrievedChunk]
    preprocessed: PreprocessedQuery
    numeric_conflict: bool


class HybridRetriever:
    def __init__(self, cfg: RetrievalConfig | None = None) -> None:
        self.cfg = cfg or load_retrieval_config()
        self.sparse_only = api_sparse_only()
        self.embed_cfg = load_embedding_config()
        self.chunk_index = ChunkIndex(self.cfg.chunks_path)
        self.bm25, self.bm25_chunk_ids = load_bm25_index(self.cfg.bm25_dir)
        self._embedder = None
        self._collection = None
        if not self.sparse_only:
            from pipeline.chroma_client import get_chroma_client
            from pipeline.embedder import EmbeddingService

            self._embedder = EmbeddingService(self.embed_cfg)
            self._chroma = get_chroma_client(self.embed_cfg)
            self._collection = self._chroma.get_collection(self.cfg.collection_name)

    def retrieve(
        self,
        query: str,
        *,
        scheme_id: str | None = None,
    ) -> RetrievalResult:
        preprocessed = preprocess_query(
            query,
            scheme_filter_min_confidence=self.cfg.scheme_filter_min_confidence,
        )
        filter_scheme = scheme_id
        if filter_scheme is None and preprocessed.apply_scheme_filter:
            filter_scheme = preprocessed.scheme.scheme_id

        amc_filter = (
            preprocessed.scheme.amc_name
            if preprocessed.scheme.amc_name
            and preprocessed.scheme.confidence >= 0.5
            and filter_scheme is None
            else None
        )

        dense_hits = self._dense_search(preprocessed.dense_query, filter_scheme)
        sparse_hits = search_bm25(
            self.bm25,
            self.bm25_chunk_ids,
            preprocessed.match_query,
            self.cfg.sparse_top_k,
        )
        if filter_scheme:
            sparse_hits = [
                (cid, score)
                for cid, score in sparse_hits
                if self._scheme_for(cid) == filter_scheme
            ]

        merged = self._rrf_merge(dense_hits, sparse_hits)
        if filter_scheme:
            merged = [c for c in merged if c.metadata.get("scheme_id") == filter_scheme]
        if amc_filter:
            merged = [
                c
                for c in merged
                if str(c.metadata.get("amc_name", "")).lower()
                == amc_filter.lower()
            ]

        reranked = self._rerank_lexical(merged, preprocessed)
        if self.cfg.use_cross_encoder:
            reranked = self._rerank_cross_encoder(
                preprocessed.dense_query,
                reranked[: self.cfg.cross_encoder_top_n],
            ) + reranked[self.cfg.cross_encoder_top_n :]

        for ch in reranked:
            ch.retrieval_score = self._final_score(ch, preprocessed)

        reranked.sort(key=lambda c: c.retrieval_score, reverse=True)
        top = reranked[: self.cfg.rerank_top_k]

        if self.cfg.merge_by_source_url:
            top = merge_chunks_by_source_url(top)

        conflict = False
        if self.cfg.detect_numeric_conflicts:
            conflict = detect_numeric_conflict(top) or chunks_contain_unsafe_numeric_spread(
                top
            )

        return RetrievalResult(
            chunks=top,
            preprocessed=preprocessed,
            numeric_conflict=conflict,
        )

    def _scheme_for(self, chunk_id: str) -> str | None:
        ch = self.chunk_index.get(chunk_id)
        return str(ch.metadata.get("scheme_id")) if ch else None

    def _final_score(self, ch: RetrievedChunk, preprocessed: PreprocessedQuery) -> float:
        q_terms = query_terms_for_match(preprocessed)
        text_words = set(re.findall(r"[a-z0-9]+", ch.text.lower()))
        overlap = len(q_terms & text_words) * 0.05
        return ch.rrf_score + overlap

    def _rerank_lexical(
        self,
        chunks: list[RetrievedChunk],
        preprocessed: PreprocessedQuery,
    ) -> list[RetrievedChunk]:
        q = preprocessed.match_query
        q_words = query_terms_for_match(preprocessed)

        def score(ch: RetrievedChunk) -> float:
            text_words = set(re.findall(r"[a-z0-9]+", ch.text.lower()))
            overlap = len(q_words & text_words)
            boost = ch.rrf_score + overlap * 0.05
            section = str(ch.metadata.get("section_canonical", ""))
            if any(
                term in q
                for term in ("expense", "sip", "nav", "aum", "rating", "minimum")
            ) and section == "key_fund_metrics":
                boost += 0.5
            if "compare similar" in ch.text.lower() or "/compare/" in ch.text.lower():
                boost -= 1.0
            ch.retrieval_score = boost
            return boost

        return sorted(chunks, key=score, reverse=True)

    def _rerank_cross_encoder(
        self,
        query: str,
        chunks: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        if not chunks:
            return chunks
        model = _get_cross_encoder(self.cfg.cross_encoder_model)
        pairs = [[query, ch.text[:512]] for ch in chunks]
        scores = model.predict(pairs)
        for ch, ce_score in zip(chunks, scores):
            ch.retrieval_score = float(ce_score) + ch.rrf_score * 0.1
        return sorted(chunks, key=lambda c: c.retrieval_score, reverse=True)

    def _dense_search(
        self,
        query: str,
        scheme_id: str | None,
    ) -> list[tuple[str, float, int]]:
        if self.sparse_only or self._embedder is None or self._collection is None:
            return []
        vector = self._embedder.embed_batch([query])[0]
        kwargs: dict = {
            "query_embeddings": [vector],
            "n_results": self.cfg.dense_top_k,
            "include": ["distances"],
        }
        if scheme_id:
            kwargs["where"] = {"scheme_id": {"$eq": scheme_id}}

        result = self._collection.query(**kwargs)
        ids = result["ids"][0]
        distances = result["distances"][0]
        hits: list[tuple[str, float, int]] = []
        for rank, (cid, dist) in enumerate(zip(ids, distances), start=1):
            if scheme_id and self._scheme_for(cid) != scheme_id:
                continue
            similarity = 1.0 - float(dist)
            if similarity < self.cfg.similarity_threshold:
                continue
            hits.append((cid, similarity, rank))
        return hits

    def _rrf_merge(
        self,
        dense_hits: list[tuple[str, float, int]],
        sparse_hits: list[tuple[str, float]],
    ) -> list[RetrievedChunk]:
        k = self.cfg.rrf_k
        scores: dict[str, float] = {}
        dense_meta: dict[str, tuple[float, int]] = {}
        sparse_meta: dict[str, tuple[float, int]] = {}

        for cid, sim, rank in dense_hits:
            scores[cid] = scores.get(cid, 0.0) + self.cfg.dense_weight / (k + rank)
            dense_meta[cid] = (sim, rank)
        for rank, (cid, score) in enumerate(sparse_hits, start=1):
            scores[cid] = scores.get(cid, 0.0) + self.cfg.sparse_weight / (k + rank)
            sparse_meta[cid] = (score, rank)

        ordered = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        out: list[RetrievedChunk] = []
        for cid, rrf in ordered:
            d = dense_meta.get(cid)
            s = sparse_meta.get(cid)
            chunk = self.chunk_index.wrap(
                cid,
                rrf_score=rrf,
                dense_similarity=d[0] if d else None,
                dense_rank=d[1] if d else None,
                sparse_rank=s[1] if s else None,
                retrieval_score=rrf,
            )
            if chunk:
                out.append(chunk)
        return out


@lru_cache(maxsize=2)
def _get_cross_encoder(model_name: str):
    from sentence_transformers import CrossEncoder

    return CrossEncoder(model_name)
