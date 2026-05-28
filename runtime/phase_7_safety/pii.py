from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_PII_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b")
_PII_PHONE = re.compile(r"\b(?:\+91[\s-]?)?[6-9]\d{9}\b")
_PII_PAN = re.compile(r"\b[A-Z]{5}[0-9]{4}[A-Z]\b")
_PII_AADHAAR = re.compile(r"\b\d{4}\s?\d{4}\s?\d{4}\b")


def redact_pii(text: str) -> tuple[str, bool]:
    """§7.3 — redact PII patterns; log detection without storing values."""
    found = False
    for name, pattern in (
        ("email", _PII_EMAIL),
        ("phone", _PII_PHONE),
        ("pan", _PII_PAN),
        ("aadhaar", _PII_AADHAAR),
    ):
        if pattern.search(text):
            found = True
            logger.info("pii_detected type=%s (redacted)", name)
            text = pattern.sub("[redacted]", text)
    return text, found
