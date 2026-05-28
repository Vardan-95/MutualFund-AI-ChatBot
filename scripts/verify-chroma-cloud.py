#!/usr/bin/env python3
"""Verify Chroma Cloud collection after ingest. Run from repo root with PYTHONPATH=."""

from __future__ import annotations

import sys

from phases.common.env import load_project_env
from pipeline.chroma_client import get_chroma_client
from pipeline.config import load_embedding_config

load_project_env()
cfg = load_embedding_config()
client = get_chroma_client(cfg)
col = client.get_collection(cfg.collection_name)
print(f"collection={cfg.collection_name} count={col.count()} database={cfg.chroma_mode}")
