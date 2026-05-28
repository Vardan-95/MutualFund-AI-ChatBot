from __future__ import annotations

import json
import pickle
from pathlib import Path

from pipeline.chunker import ChunkRecord
from pipeline.chroma_client import get_chroma_client
from pipeline.config import EmbeddingConfig

_BATCH_ADD = 100


def write_vectors(
    chunks: list[ChunkRecord],
    ids: list[str],
    vectors: list[list[float]],
    config: EmbeddingConfig,
) -> tuple[str, int]:
    """Persist vectors to Chroma Cloud (default) or local Chroma / numpy fallback."""
    if config.chroma_mode == "cloud":
        count = _write_chroma_collection(chunks, ids, vectors, config)
        return "chroma_cloud", count

    try:
        count = _write_chroma_collection(chunks, ids, vectors, config)
        return "chroma_local", count
    except Exception as exc:
        print(f"Local Chroma unavailable ({exc}); using numpy fallback.")
        count = _write_numpy(chunks, ids, vectors, config)
        return "numpy", count


def _chunk_rows(
    chunks: list[ChunkRecord],
    ids: list[str],
) -> tuple[list[str], list[dict], list[str]]:
    id_to_chunk = {c.chunk_id: c for c in chunks}
    metadatas: list[dict] = []
    documents: list[str] = []
    for cid in ids:
        ch = id_to_chunk[cid]
        metadatas.append({k: str(v) for k, v in ch.metadata.items()})
        documents.append(ch.text)
    return ids, metadatas, documents


def _write_chroma_collection(
    chunks: list[ChunkRecord],
    ids: list[str],
    vectors: list[list[float]],
    config: EmbeddingConfig,
) -> int:
    client = get_chroma_client(config)
    try:
        client.delete_collection(config.collection_name)
    except Exception:
        pass
    collection = client.create_collection(name=config.collection_name)
    _, metadatas, documents = _chunk_rows(chunks, ids)

    for start in range(0, len(ids), _BATCH_ADD):
        end = start + _BATCH_ADD
        collection.add(
            ids=ids[start:end],
            embeddings=vectors[start:end],
            metadatas=metadatas[start:end],
            documents=documents[start:end],
        )
    return collection.count()


def _write_numpy(
    chunks: list[ChunkRecord],
    ids: list[str],
    vectors: list[list[float]],
    config: EmbeddingConfig,
) -> int:
    out_dir = Path(config.chroma_persist_dir).parent / "vectors_numpy"
    out_dir.mkdir(parents=True, exist_ok=True)
    id_to_chunk = {c.chunk_id: c for c in chunks}
    store = {
        "ids": ids,
        "vectors": vectors,
        "documents": [id_to_chunk[i].text for i in ids],
        "metadatas": [id_to_chunk[i].metadata for i in ids],
        "collection_name": config.collection_name,
    }
    with (out_dir / "store.pkl").open("wb") as f:
        pickle.dump(store, f)
    (out_dir / "meta.json").write_text(
        json.dumps({"count": len(ids), "backend": "numpy"}),
        encoding="utf-8",
    )
    return len(ids)
