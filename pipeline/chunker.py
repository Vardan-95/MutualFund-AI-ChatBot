from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from pipeline.config import ChunkingConfig
from pipeline.normalize import NormalizedDocument
from pipeline.tokens import count_tokens


@dataclass
class ChunkRecord:
    chunk_id: str
    text: str
    token_count: int
    metadata: dict = field(default_factory=dict)


def _section_canonical(title: str) -> str:
    key = title.strip().lower().replace(" ", "_")
    mapping = {
        "key_fund_metrics": "key_fund_metrics",
        "fund_overview": "fund_overview",
        "investment_limits": "investment_limits",
        "fees_and_loads": "fees_and_loads",
        "risk_and_benchmark": "risk_and_benchmark",
        "returns_and_nav": "returns_and_nav",
        "fund_details": "fund_details",
        "holdings_and_portfolio": "holdings_and_portfolio",
        "tax_and_lock-in": "tax_and_lock_in",
        "tax_and_lock_in": "tax_and_lock_in",
    }
    return mapping.get(key, "other")


def _make_chunk_id(scheme_id: str, section: str, text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:8]
    return f"{scheme_id}::{section}::{digest}"


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [p for p in parts if p.strip()]


def _window_chunks(text: str, cfg: ChunkingConfig) -> list[str]:
    sentences = _split_sentences(text)
    if not sentences:
        return [text] if text.strip() else []
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0
    for sent in sentences:
        st = count_tokens(sent, cfg.token_encoding)
        if current_tokens + st > cfg.max_section_tokens and current:
            chunks.append(" ".join(current))
            overlap: list[str] = []
            overlap_tokens = 0
            for s in reversed(current):
                t = count_tokens(s, cfg.token_encoding)
                if overlap_tokens + t > cfg.sentence_overlap_tokens:
                    break
                overlap.insert(0, s)
                overlap_tokens += t
            current = overlap + [sent]
            current_tokens = count_tokens(" ".join(current), cfg.token_encoding)
        else:
            current.append(sent)
            current_tokens += st
    if current:
        chunks.append(" ".join(current))
    return chunks


def _split_section(text: str, cfg: ChunkingConfig) -> list[str]:
    tokens = count_tokens(text, cfg.token_encoding)
    if tokens <= cfg.max_section_tokens:
        return [text.strip()] if text.strip() else []
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if len(paragraphs) > 1:
        parts: list[str] = []
        buf: list[str] = []
        buf_tokens = 0
        for para in paragraphs:
            pt = count_tokens(para, cfg.token_encoding)
            if buf_tokens + pt > cfg.max_section_tokens and buf:
                parts.append("\n\n".join(buf))
                buf = [para]
                buf_tokens = pt
            else:
                buf.append(para)
                buf_tokens += pt
        if buf:
            parts.append("\n\n".join(buf))
        if all(count_tokens(p, cfg.token_encoding) <= cfg.max_section_tokens for p in parts):
            return parts
    return _window_chunks(text, cfg)


def _ensure_max_size(text: str, cfg: ChunkingConfig) -> list[str]:
    if count_tokens(text, cfg.token_encoding) <= cfg.hard_max_tokens:
        return [text]
    return _window_chunks(text, cfg)


def chunk_document(
    norm: NormalizedDocument,
    cfg: ChunkingConfig,
    corpus_version: int,
) -> list[ChunkRecord]:
    meta = norm.document.metadata
    scheme_id = meta["scheme_id"]
    sections = re.split(r"(?m)^##\s+", norm.body)
    chunks: list[ChunkRecord] = []
    ingested_at = datetime.now(timezone.utc).astimezone().isoformat()

    if sections and not sections[0].strip().startswith("#"):
        preamble = sections[0].strip()
        if preamble:
            sections = ["Other\n" + preamble] + sections[1:]

    for raw in sections:
        raw = raw.strip()
        if not raw:
            continue
        lines = raw.split("\n", 1)
        title = lines[0].strip()
        body = lines[1].strip() if len(lines) > 1 else ""
        if not body:
            continue
        section = _section_canonical(title)
        parts = _split_section(body, cfg)
        flat_parts: list[str] = []
        for part in parts:
            flat_parts.extend(_ensure_max_size(part, cfg))

        for idx, part in enumerate(flat_parts):
            if count_tokens(part, cfg.token_encoding) < cfg.min_chunk_tokens and cfg.merge_short_sections:
                if chunks and chunks[-1].metadata.get("scheme_id") == scheme_id:
                    merged = chunks[-1].text + "\n\n" + part
                    if count_tokens(merged, cfg.token_encoding) <= cfg.hard_max_tokens:
                        chunks[-1].text = merged
                        chunks[-1].token_count = count_tokens(merged, cfg.token_encoding)
                        continue
            chunk_meta = {
                "source_url": meta["source_url"],
                "source_domain": "groww.in",
                "document_type": meta.get("document_type", "groww_scheme_page"),
                "scheme_id": scheme_id,
                "scheme_name": meta["scheme_name"],
                "scheme_category": meta["scheme_category"],
                "amc_name": meta["amc_name"],
                "section_title": title,
                "section_canonical": section,
                "chunk_index": idx,
                "chunk_count_in_section": len(flat_parts),
                "content_hash": norm.content_hash,
                "content_captured_at": meta.get("content_captured_at", ""),
                "corpus_version": corpus_version,
                "ingested_at": ingested_at,
            }
            chunks.append(
                ChunkRecord(
                    chunk_id=_make_chunk_id(scheme_id, section, part),
                    text=part,
                    token_count=count_tokens(part, cfg.token_encoding),
                    metadata=chunk_meta,
                )
            )

    if cfg.dense_fact_chunk_enabled and "key fund metrics" in norm.body.lower():
        m = re.search(
            r"## Key fund metrics\s*\n((?:\|[^\n]+\n?)+)",
            norm.body,
            re.I,
        )
        if m:
            block = m.group(1).strip()
            if block and count_tokens(block, cfg.token_encoding) >= 40:
                cid = _make_chunk_id(scheme_id, "key_facts_at_a_glance", block)
                if not any(c.chunk_id == cid for c in chunks):
                    glance_meta = {
                        "source_url": meta["source_url"],
                        "source_domain": "groww.in",
                        "document_type": meta.get("document_type", "groww_scheme_page"),
                        "scheme_id": scheme_id,
                        "scheme_name": meta["scheme_name"],
                        "scheme_category": meta["scheme_category"],
                        "amc_name": meta["amc_name"],
                        "section_title": "Key facts at a glance",
                        "section_canonical": "key_fund_metrics",
                        "content_hash": norm.content_hash,
                        "content_captured_at": meta.get("content_captured_at", ""),
                        "corpus_version": corpus_version,
                        "ingested_at": ingested_at,
                    }
                    chunks.insert(
                        0,
                        ChunkRecord(
                            chunk_id=cid,
                            text=block,
                            token_count=count_tokens(block, cfg.token_encoding),
                            metadata=glance_meta,
                        ),
                    )
    return chunks
