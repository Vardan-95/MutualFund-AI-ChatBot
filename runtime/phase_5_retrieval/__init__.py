"""Phase 5 — retrieval layer (BGE + Chroma + hybrid merge + citation)."""

from runtime.phase_5_retrieval.citation import CitationResult, select_citation
from runtime.phase_5_retrieval.preprocess import PreprocessedQuery, preprocess_query
from runtime.phase_5_retrieval.retriever import HybridRetriever, RetrievalResult

__all__ = [
    "CitationResult",
    "HybridRetriever",
    "PreprocessedQuery",
    "RetrievalResult",
    "preprocess_query",
    "select_citation",
]
