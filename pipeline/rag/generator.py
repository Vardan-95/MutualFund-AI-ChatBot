"""Generation layer — delegates to runtime.phase_6_generation."""

from __future__ import annotations

from pipeline.rag.config import RagConfig
from runtime.phase_6_generation.config import GenerationConfig, load_generation_config
from runtime.phase_6_generation.generator import GenerationResult, generate_body, templated_safe_fallback
from runtime.phase_5_retrieval.models import RetrievedChunk


def generate_answer(
    query: str,
    chunks: list[RetrievedChunk],
    *,
    cfg: RagConfig,
    intent: str,
    strict: bool = False,
) -> str:
    gen_cfg = _rag_to_gen_cfg(cfg)
    result = generate_body(query, chunks, cfg=gen_cfg, strict=strict)
    return result.body


def _rag_to_gen_cfg(cfg: RagConfig) -> GenerationConfig:
    base = load_generation_config()
    return GenerationConfig(
        max_sentences=cfg.max_sentences,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        llm_provider=cfg.llm_provider,
        llm_model=cfg.llm_model,
        llm_base_url=cfg.llm_base_url,
        footer_policy=base.footer_policy,
    )


__all__ = ["generate_answer", "GenerationResult", "templated_safe_fallback"]
