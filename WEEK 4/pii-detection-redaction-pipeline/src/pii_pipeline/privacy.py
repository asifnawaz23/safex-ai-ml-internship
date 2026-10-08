"""
privacy.py
----------
Privacy and security safeguards used by the pipeline and CLI.

- Path validation: inputs/outputs must stay inside allowed directories.
- Synthetic-only guard: refuses text with email domains outside
  example.com / example.org / example.net and datasets not marked synthetic.
- Size and type limits on document text.
- Masking helpers for previews and reports (never for redaction itself).
- A logging filter that masks email-, phone-, CNIC- and account-like strings
  in log records, as a second line of defence. Pipeline code logs only ids,
  counts and labels.
- Keyed pseudonyms (HMAC-SHA256) with a key from an environment variable.
- Separation check for originals / annotations / redacted output.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Optional, Sequence

from pii_pipeline import config

logger = logging.getLogger(__name__)

MAX_DOCUMENT_LENGTH = config.MAX_DOCUMENT_CHARS
ALLOWED_EXTENSIONS = {".txt", ".csv", ".json", ".jsonl", ".md"}


class PrivacyGuardError(ValueError):
    """Raised when an input violates a privacy safeguard (CLI exit code 2)."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def ensure_within(path, root) -> Path:
    """Resolve ``path`` and require it to be inside ``root``."""
    p = Path(path).resolve()
    r = Path(root).resolve()
    try:
        p.relative_to(r)
    except ValueError:
        raise PrivacyGuardError(f"Path is outside the allowed directory {r}") from None
    return p


def validate_input_path(path, allowed_root: Optional[Path] = None) -> Path:
    """Existing file, allowed extension, optionally inside ``allowed_root``."""
    p = Path(path).resolve()
    if allowed_root is not None:
        ensure_within(p, allowed_root)
    if not p.exists():
        raise PrivacyGuardError(f"Path does not exist: {p.name}")
    if not p.is_file():
        raise PrivacyGuardError(f"Path is not a file: {p.name}")
    if p.suffix.lower() not in ALLOWED_EXTENSIONS:
        raise PrivacyGuardError(f"File extension {p.suffix!r} is not allowed")
    return p


def allowed_input_roots() -> list:
    return [config.ROOT / d for d in config.get("privacy.allowed_input_dirs", ["data"])]


def validate_user_input_file(path) -> Path:
    """A file passed on the CLI must live under one of the allowed input dirs."""
    for root in allowed_input_roots():
        try:
            return validate_input_path(path, root)
        except PrivacyGuardError as exc:
            if "outside" in str(exc):
                continue
            raise
    raise PrivacyGuardError("Input files must be inside: " +
                            ", ".join(str(r.relative_to(config.ROOT)) for r in allowed_input_roots()))


def validate_output_path(path, allowed_root: Optional[Path] = None) -> Path:
    p = Path(path).resolve()
    if allowed_root is not None:
        ensure_within(p, allowed_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def validate_output_dir_separation(originals_dir, annotations_dir, redacted_dir) -> None:
    """Originals/annotations and redacted output must not share a directory tree."""
    o, a, r = (Path(x).resolve() for x in (originals_dir, annotations_dir, redacted_dir))
    for src in (o, a):
        if r == src or src in r.parents or r in src.parents:
            raise PrivacyGuardError("Redacted output must be stored separately from originals and annotations")


# ---------------------------------------------------------------------------
# Content checks
# ---------------------------------------------------------------------------

def validate_document_text(text) -> str:
    if not isinstance(text, str):
        raise TypeError(f"Document text must be str, got {type(text).__name__}")
    if len(text) > MAX_DOCUMENT_LENGTH:
        raise PrivacyGuardError(f"Document exceeds {MAX_DOCUMENT_LENGTH} characters")
    return text


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@([A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+)")


def assert_synthetic_text(text: str, allowed_domains: Sequence[str] = None) -> str:
    """Refuse text containing email addresses on non-reserved domains.

    This is a practical tripwire against pasting real data; it cannot prove
    that text is synthetic.
    """
    validate_document_text(text)
    allowed = {d.lower() for d in (allowed_domains or config.ALLOWED_EMAIL_DOMAINS)}
    for m in _EMAIL_RE.finditer(text):
        domain = m.group(1).lower()
        if domain not in allowed:
            raise PrivacyGuardError(
                "Text contains an email address outside the reserved example.com/.org/.net "
                "domains; only synthetic data may be processed")
    return text


def assert_synthetic_rows(rows: Iterable[dict]) -> None:
    for row in rows:
        if str(row.get("synthetic", "")).strip().lower() != "true":
            raise PrivacyGuardError("Dataset rows must carry synthetic=true; refusing to process")


# ---------------------------------------------------------------------------
# Masking (previews, reports, logs) — not a redaction method
# ---------------------------------------------------------------------------

def mask_value(value: str) -> str:
    """Keep the first and last two characters of long values, mask the rest."""
    if not value:
        return ""
    if len(value) >= 8:
        return value[:2] + "*" * (len(value) - 4) + value[-2:]
    return value[0] + "*" * (len(value) - 1)


def mask_pii_for_log(text: str, max_len: int = 6) -> str:
    """Backward-compatible alias kept for log lines."""
    return mask_value(text)


_LOG_PATTERNS = [
    (re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9\-]+(?:\.[A-Za-z0-9\-]+)+"), "[EMAIL]"),
    (re.compile(r"\bUBW-\d{5}\b", re.IGNORECASE), "[CUSTOMER_ID]"),
    (re.compile(r"\b\d{5}[- ]?\d{7}[- ]?\d\b"), "[CNIC]"),
    (re.compile(r"(?:\+|\b)\d[\d\s\-.()]{8,}\d\b"), "[NUMBER]"),
]


def mask_log_text(text: str) -> str:
    for pat, repl in _LOG_PATTERNS:
        text = pat.sub(repl, text)
    return text


class RawTextRedactingFilter(logging.Filter):
    """Mask PII-like substrings in every log record passing through."""

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            msg = record.getMessage()
        except Exception:
            return True
        record.msg = mask_log_text(msg)
        record.args = None
        return True


def install_log_filter(target_logger: logging.Logger) -> RawTextRedactingFilter:
    flt = RawTextRedactingFilter()
    target_logger.addFilter(flt)
    for h in target_logger.handlers:
        h.addFilter(flt)
    return flt


# ---------------------------------------------------------------------------
# Keyed pseudonyms
# ---------------------------------------------------------------------------

def keyed_pseudonym(value: str, key: Optional[str] = None) -> str:
    """HMAC-SHA256 pseudonym of ``value`` (hex).

    The key comes from the environment variable named in settings
    (PII_PIPELINE_HMAC_KEY) unless passed explicitly. Without the key, an
    attacker cannot simply hash all ~10^10 Pakistani mobile numbers or CNICs
    and compare digests, which is exactly what makes plain SHA-256 of such
    predictable identifiers unsafe. Whoever holds the key CAN do that, so the
    key must be protected like the original data. A pseudonym is not
    anonymisation.
    """
    if key is None:
        key = os.environ.get(config.HMAC_KEY_ENV)
    if not key:
        raise RuntimeError(f"Set the {config.HMAC_KEY_ENV} environment variable to use keyed pseudonyms")
    return hmac.new(key.encode("utf-8"), value.encode("utf-8"), hashlib.sha256).hexdigest()


# ---------------------------------------------------------------------------
# Dry-run preview
# ---------------------------------------------------------------------------

def preview_detections(text: str, predictions: Sequence, max_preview: int = 10) -> str:
    """Masked, human-readable list of detections for dry-run mode."""
    lines = [f"Detections: {len(predictions)}"]
    for i, p in enumerate(predictions[:max_preview]):
        label = getattr(p, "label", None) or getattr(p, "entity_type", "?")
        lines.append(f"  [{i + 1}] {label:<13} pos={p.start}:{p.end} score={p.score:.2f} "
                     f"value={mask_value(text[p.start:p.end])!r}")
    if len(predictions) > max_preview:
        lines.append(f"  ... and {len(predictions) - max_preview} more")
    return "\n".join(lines)
