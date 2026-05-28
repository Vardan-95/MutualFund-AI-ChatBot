from __future__ import annotations

import os

from runtime.phase_6_generation.config import GenerationConfig
from runtime.phase_6_generation.context import build_user_message
from runtime.phase_6_generation.prompts import SYSTEM_PROMPT, SYSTEM_PROMPT_STRICT
from runtime.phase_5_retrieval.models import RetrievedChunk


def resolve_client(cfg: GenerationConfig) -> tuple[object, str, str] | None:
    from openai import OpenAI

    if os.environ.get("GROQ_API_KEY", "").strip():
        return (
            OpenAI(
                api_key=os.environ["GROQ_API_KEY"].strip(),
                base_url=cfg.llm_base_url or "https://api.groq.com/openai/v1",
            ),
            os.environ.get("GROQ_MODEL", cfg.llm_model),
            "Groq",
        )
    if os.environ.get("OPENAI_API_KEY", "").strip():
        kwargs: dict = {"api_key": os.environ["OPENAI_API_KEY"].strip()}
        if cfg.llm_base_url:
            kwargs["base_url"] = cfg.llm_base_url
        return (
            OpenAI(**kwargs),
            os.environ.get("OPENAI_MODEL", cfg.llm_model),
            "OpenAI",
        )
    return None


def chat_completion(
    client: object,
    model: str,
    query: str,
    chunks: list[RetrievedChunk],
    cfg: GenerationConfig,
    *,
    strict: bool,
) -> str:
    response = client.chat.completions.create(  # type: ignore[union-attr]
        model=model,
        temperature=cfg.temperature,
        max_tokens=cfg.max_tokens,
        messages=[
            {
                "role": "system",
                "content": SYSTEM_PROMPT_STRICT if strict else SYSTEM_PROMPT,
            },
            {"role": "user", "content": build_user_message(query, chunks)},
        ],
    )
    return (response.choices[0].message.content or "").strip()
