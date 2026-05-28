from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from phases.common.env import require_chroma_app_env

if TYPE_CHECKING:
    from pipeline.config import EmbeddingConfig


def get_chroma_client(config: EmbeddingConfig) -> Any:
    """Return a Chroma client for local persistence or Chroma Cloud."""
    import chromadb

    if config.chroma_mode == "cloud":
        require_chroma_app_env()
        kwargs: dict[str, Any] = {
            "api_key": os.environ["CHROMA_API_KEY"].strip(),
            "tenant": os.environ["CHROMA_TENANT"].strip(),
            "database": os.environ["CHROMA_DATABASE"].strip(),
        }
        host = (os.environ.get("CHROMA_HOST") or config.chroma_cloud_host or "").strip()
        if host:
            host = host.replace("https://", "").replace("http://", "").split("/")[0]
            kwargs["cloud_host"] = host
            kwargs["cloud_port"] = 443
            kwargs["enable_ssl"] = True
        return chromadb.CloudClient(**kwargs)

    from pathlib import Path

    persist = Path(config.chroma_persist_dir)
    persist.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(persist))
