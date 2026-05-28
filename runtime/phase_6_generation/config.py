from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from phases.common.config_loader import load_yaml
from phases.common.paths import CONFIG_DIR


@dataclass(frozen=True)
class GenerationConfig:
    max_sentences: int
    temperature: float
    max_tokens: int
    llm_provider: str
    llm_model: str
    llm_base_url: str
    footer_policy: str  # cited_source | max_chunks


def _resolve_provider(generation: dict) -> str:
    env = os.environ.get("LLM_PROVIDER", "").strip().lower()
    if env in ("groq", "openai"):
        return env
    return str(generation.get("provider", "groq")).lower()


def load_generation_config(path: Path | None = None) -> GenerationConfig:
    data = load_yaml(path or CONFIG_DIR / "rag.yaml")
    generation = data.get("generation", {})
    provider = _resolve_provider(generation)
    if provider == "groq":
        model = os.environ.get(
            "GROQ_MODEL",
            str(generation.get("model", "llama-3.3-70b-versatile")),
        )
        base_url = os.environ.get(
            "GROQ_BASE_URL",
            str(generation.get("groq_base_url", "https://api.groq.com/openai/v1")),
        )
    else:
        model = os.environ.get("OPENAI_MODEL", str(generation.get("model", "gpt-4o-mini")))
        base_url = os.environ.get("OPENAI_BASE_URL", str(generation.get("openai_base_url", "")))

    return GenerationConfig(
        max_sentences=int(generation.get("max_sentences", 3)),
        temperature=float(generation.get("temperature", 0.1)),
        max_tokens=int(generation.get("max_tokens", 180)),
        llm_provider=provider,
        llm_model=model,
        llm_base_url=base_url,
        footer_policy=str(generation.get("footer_policy", "cited_source")),
    )
