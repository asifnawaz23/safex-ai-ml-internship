"""
redactor.py
-----------
Redaction with Presidio AnonymizerEngine plus an offset-independent residual
check.

Operators
    One ``replace`` operator per canonical label, from settings.json
    entities.redaction_map (PERSON -> [PERSON], PHONE_NUMBER -> [PHONE], ...).
    Any other label falls back to "DEFAULT" -> [REDACTED].

Conflict handling (deterministic)
    ConflictResolutionStrategy.REMOVE_INTERSECTIONS: when two detections
    overlap, Presidio trims the lower-scored one so that every character that
    was covered by any detection is still replaced. No partially redacted
    value is left behind by an overlap. Presidio's default
    merge_entities_with_spaces=True also merges same-label detections that are
    separated only by whitespace.

Residual check
    ``find_residuals`` searches the REDACTED text for each planted value. It
    does not reuse the original offsets (they are invalid after replacement).
    Values are matched case-insensitively with alphanumeric boundaries; for
    PHONE_NUMBER and CNIC the digits are also matched with any separators in
    between, so "0321-1234567" surviving as "03211234567" is still reported.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence

import regex as re
from presidio_anonymizer import AnonymizerEngine
from presidio_anonymizer.entities import (
    ConflictResolutionStrategy, OperatorConfig, RecognizerResult,
)

from pii_pipeline import config
from pii_pipeline.evaluation import Prediction
from pii_pipeline.privacy import mask_value

logger = logging.getLogger(__name__)

_ENGINE = AnonymizerEngine()
CONFLICT_STRATEGY = ConflictResolutionStrategy(config.get("redaction.conflict_resolution",
                                                          "remove_intersections"))


def build_operators(redaction_map: Dict[str, str] = None) -> Dict[str, OperatorConfig]:
    redaction_map = redaction_map or config.REDACTION_MAP
    ops = {label: OperatorConfig("replace", {"new_value": ph}) for label, ph in redaction_map.items()}
    ops["DEFAULT"] = OperatorConfig("replace", {"new_value": config.FALLBACK_PLACEHOLDER})
    return ops


_OPERATORS = build_operators()


@dataclass
class RedactionResult:
    text: str
    n_replaced: int
    labels: List[str]


def redact_text(text: str, predictions: Sequence[Prediction], record_id: str = "") -> RedactionResult:
    """Replace every predicted span with its placeholder using AnonymizerEngine."""
    if not predictions:
        return RedactionResult(text, 0, [])
    analyzer_results = [RecognizerResult(p.label, p.start, p.end, p.score) for p in predictions]
    try:
        out = _ENGINE.anonymize(text=text, analyzer_results=analyzer_results,
                                operators=_OPERATORS, conflict_resolution=CONFLICT_STRATEGY)
    except Exception as exc:
        # Never log the text or values; type and record id only.
        logger.error("Anonymizer failed for record %s (%s)", record_id or "?", type(exc).__name__)
        raise
    return RedactionResult(out.text, len(out.items), sorted(i.entity_type for i in out.items))


@dataclass
class Residual:
    record_id: str
    annotation_id: str
    entity_type: str
    masked_value: str
    match_kind: str          # exact | digits


def _value_pattern(value: str) -> re.Pattern:
    return re.compile(r"(?<![\p{L}\p{N}])" + re.escape(value) + r"(?![\p{L}\p{N}])", re.IGNORECASE)


_SEP = r"[\s\-.()+]*"


def _digits_pattern(value: str, entity_type: str):
    digits = re.sub(r"\D", "", value)
    if len(digits) < 7:
        return None
    if entity_type == "PHONE_NUMBER" and len(digits) >= 10:
        # Match the 10-digit national number with any (or no) PK prefix, so a
        # value planted as +92 3XX... is still found if it survives as 03XX...
        core = _SEP.join(digits[-10:])
        return re.compile(r"(?<!\d)(?:(?:\+?92|0092|0)" + _SEP + r")?" + core + r"(?!\d)")
    return re.compile(r"(?<!\d)" + _SEP.join(digits) + r"(?!\d)")


def find_residuals(redacted_text: str, gt_entities: Iterable) -> List[Residual]:
    """Planted values that still appear in the redacted text."""
    found: List[Residual] = []
    for g in gt_entities:
        kind = None
        if _value_pattern(g.text).search(redacted_text):
            kind = "exact"
        elif g.entity_type in ("PHONE_NUMBER", "CNIC"):
            pat = _digits_pattern(g.text, g.entity_type)
            if pat is not None and pat.search(redacted_text):
                kind = "digits"
        if kind:
            found.append(Residual(g.record_id, g.annotation_id, g.entity_type, mask_value(g.text), kind))
    return found
