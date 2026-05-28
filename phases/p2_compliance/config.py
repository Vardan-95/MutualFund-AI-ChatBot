from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from phases.common.config_loader import load_yaml
from phases.common.paths import CONFIG_DIR


@dataclass(frozen=True)
class ComplianceConfig:
    education_url: str
    advisory_similarity_threshold: float
    comparison_similarity_threshold: float
    advisory_exemplars: list[str]
    comparison_exemplars: list[str]
    advisory_patterns: list[str]
    comparison_patterns: list[str]
    performance_patterns: list[str]
    process_patterns: list[str]
    out_of_scope_amc_keywords: list[str]
    max_sentences: int
    block_performance_synthesis: bool
    redact_pii: bool
    forbidden_output_patterns: list[str]


def load_compliance_config(path: Path | None = None) -> ComplianceConfig:
    data = load_yaml(path or CONFIG_DIR / "compliance.yaml")
    patterns = data.get("patterns", {})
    exemplars = data.get("refusal_exemplars", {})
    guardrails = data.get("guardrails", {})
    return ComplianceConfig(
        education_url=str(
            data.get(
                "education_url",
                "https://www.amfiindia.com/investor/knowledge-center-info?zoneName=IntroductionToMF",
            )
        ),
        advisory_similarity_threshold=float(data.get("advisory_similarity_threshold", 0.78)),
        comparison_similarity_threshold=float(data.get("comparison_similarity_threshold", 0.76)),
        advisory_exemplars=list(exemplars.get("advisory", [])),
        comparison_exemplars=list(exemplars.get("comparison", [])),
        advisory_patterns=list(patterns.get("advisory", [])),
        comparison_patterns=list(patterns.get("comparison", [])),
        performance_patterns=list(patterns.get("performance", [])),
        process_patterns=list(patterns.get("process", [])),
        out_of_scope_amc_keywords=list(data.get("out_of_scope_amc_keywords", [])),
        max_sentences=int(guardrails.get("max_sentences", 3)),
        block_performance_synthesis=bool(guardrails.get("block_performance_synthesis", True)),
        redact_pii=bool(guardrails.get("redact_pii", True)),
        forbidden_output_patterns=list(
            guardrails.get(
                "forbidden_output_patterns",
                [
                    "invest in",
                    "you should",
                    "better than",
                    "outperform",
                    "guarantee",
                    "best fund",
                    "recommend",
                ],
            )
        ),
    )
