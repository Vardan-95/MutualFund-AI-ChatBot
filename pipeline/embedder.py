from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

from pipeline.chunker import ChunkRecord
from pipeline.config import EmbeddingConfig

# Keep sentence-transformers on torch-only path in local/runtime environments.
os.environ.setdefault("USE_TF", "0")
os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
os.environ.setdefault("TRANSFORMERS_NO_JAX", "1")


def _l2_normalize(vec: list[float]) -> list[float]:
    arr = np.array(vec, dtype=np.float32)
    norm = np.linalg.norm(arr)
    if norm == 0:
        return vec
    return (arr / norm).tolist()


class EmbeddingService:
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config
        self._local_model = None

    def _hash_embed_texts(self, texts: list[str]) -> list[list[float]]:
        import hashlib

        dims = int(self.config.dimensions or 384)
        out: list[list[float]] = []
        for text in texts:
            buf = bytearray()
            seed = text.encode("utf-8", errors="ignore")
            while len(buf) < dims * 4:
                seed = hashlib.sha256(seed).digest()
                buf.extend(seed)
            vals: list[float] = []
            for i in range(dims):
                n = int.from_bytes(buf[i * 4 : i * 4 + 4], "little", signed=False)
                vals.append(((n / 4294967295.0) * 2.0) - 1.0)
            out.append(vals)
        return out

    def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        try:
            from sentence_transformers import SentenceTransformer

            if self._local_model is None:
                self._local_model = SentenceTransformer(self.config.model)
            vectors = self._local_model.encode(texts, show_progress_bar=False)
            return [v.tolist() for v in vectors]
        except Exception:
            # Fallback keeps runtime functional if local transformer stack is broken.
            return self._hash_embed_texts(texts)

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        vectors = self._embed_texts(texts)
        if self.config.normalize_vectors:
            vectors = [_l2_normalize(v) for v in vectors]
        return vectors

    def _cache_path(self, chunk: ChunkRecord) -> Path:
        import hashlib

        safe_name = hashlib.sha256(chunk.chunk_id.encode("utf-8")).hexdigest()
        return Path(self.config.cache_dir) / f"{safe_name}.json"

    def embed_chunks(
        self,
        chunks: list[ChunkRecord],
        force: bool = False,
    ) -> tuple[list[str], list[list[float]], int]:
        ids: list[str] = []
        vectors: list[list[float]] = []
        skipped = 0
        cache_dir = Path(self.config.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        batch_texts: list[str] = []
        batch_chunks: list[ChunkRecord] = []

        def flush_batch() -> None:
            nonlocal batch_texts, batch_chunks, skipped
            if not batch_texts:
                return
            embedded = self.embed_batch(batch_texts)
            for ch, vec in zip(batch_chunks, embedded):
                ids.append(ch.chunk_id)
                vectors.append(vec)
                cache_file = self._cache_path(ch)
                cache_file.write_text(
                    json.dumps(
                        {
                            "chunk_id": ch.chunk_id,
                            "content_hash": ch.metadata.get("content_hash"),
                            "vector": vec,
                            "model": self.config.model,
                        }
                    ),
                    encoding="utf-8",
                )
            batch_texts = []
            batch_chunks = []

        for chunk in chunks:
            cache_file = self._cache_path(chunk)
            if (
                not force
                and cache_file.exists()
                and json.loads(cache_file.read_text(encoding="utf-8")).get("content_hash")
                == chunk.metadata.get("content_hash")
            ):
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                ids.append(chunk.chunk_id)
                vectors.append(data["vector"])
                skipped += 1
                continue

            text = chunk.text
            if self.config.prefix_scheme_name:
                text = f"{chunk.metadata.get('scheme_name')} | {chunk.metadata.get('section_title')}: {text}"
            batch_texts.append(text)
            batch_chunks.append(chunk)
            if len(batch_texts) >= self.config.batch_size:
                flush_batch()
        flush_batch()
        return ids, vectors, skipped


