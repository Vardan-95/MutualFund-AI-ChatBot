from __future__ import annotations

import os
from dataclasses import replace

from phases.p2_compliance.config import ComplianceConfig, load_compliance_config
from pipeline.rag.config import RagConfig, load_rag_config


def load_safety_config() -> tuple[ComplianceConfig, RagConfig]:
    compliance = load_compliance_config()
    rag = load_rag_config()
    edu = os.environ.get("EDUCATIONAL_URL", "").strip()
    if edu:
        compliance = replace(compliance, education_url=edu)
        rag = replace(rag, refusal_education_url=edu)
    return compliance, rag
