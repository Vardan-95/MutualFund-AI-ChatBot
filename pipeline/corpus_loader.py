from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import frontmatter

from phases.common.config_loader import SchemeSource, load_sources_config
from phases.common.paths import PROJECT_ROOT
from pipeline.config import allowed_source_urls

REQUIRED_FRONT_MATTER = (
    "source_url",
    "scheme_name",
    "scheme_id",
    "amc_name",
    "scheme_category",
    "content_captured_at",
)


@dataclass
class CorpusDocument:
    path: Path
    scheme: SchemeSource
    metadata: dict
    body: str

    @property
    def scheme_id(self) -> str:
        return self.metadata["scheme_id"]


class CorpusValidationError(Exception):
    pass


def load_corpus_documents(corpus_dir: Path) -> list[CorpusDocument]:
    """§4.3 Load and validate all corpus markdown files."""
    sources_cfg = load_sources_config()
    allowlist = allowed_source_urls()
    by_id = {s.scheme_id: s for s in sources_cfg.sources}
    documents: list[CorpusDocument] = []

    for scheme in sources_cfg.sources:
        path = PROJECT_ROOT / scheme.corpus_file
        if not path.exists():
            raise CorpusValidationError(f"Missing corpus file: {scheme.corpus_file}")

        post = frontmatter.load(path)
        meta = dict(post.metadata)
        _validate_front_matter(meta, path)
        url = meta["source_url"]
        if url not in allowlist:
            raise CorpusValidationError(f"source_url not in citation allowlist: {url}")
        if meta["scheme_id"] not in by_id:
            raise CorpusValidationError(f"Unknown scheme_id: {meta['scheme_id']}")
        if by_id[meta["scheme_id"]].source_url != url:
            raise CorpusValidationError(
                f"source_url mismatch for {meta['scheme_id']}: {url}"
            )

        documents.append(
            CorpusDocument(path=path, scheme=by_id[meta["scheme_id"]], metadata=meta, body=post.content)
        )

    return documents


def _validate_front_matter(meta: dict, path: Path) -> None:
    missing = [k for k in REQUIRED_FRONT_MATTER if k not in meta or meta[k] in (None, "")]
    if missing:
        raise CorpusValidationError(f"{path}: missing front matter fields: {missing}")
