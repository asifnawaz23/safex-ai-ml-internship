"""
ground_truth.py
---------------
Save, load and validate the ground truth produced by the synthetic generator.

The ground truth is created while documents are assembled (offsets recorded at
append time, see synthetic_data._DocBuilder). It is never derived from detector
output.

Annotation schema (JSON array / CSV columns)
    annotation_id      str   e.g. REC-00001-E02
    record_id          str
    doc_type           str
    entity_type        str   one of synthetic_data.ENTITY_TYPES
    text               str   exact planted substring
    start              int   0-based, inclusive
    end                int   0-based, exclusive
    source             str   planted | challenge
    expected_handling  str   REDACT
    tags               list  edge-case tags (CSV: ';'-joined)

False-positive trap schema (fp_traps.json)
    trap_id, record_id, doc_type, kind, text, start, end,
    expected_handling (KEEP), tags
"""

import csv
import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List

from pii_pipeline.synthetic_data import (
    ENTITY_TYPES, PlantedEntity, SyntheticRecord, TrapAnnotation,
)

logger = logging.getLogger(__name__)

GT_CSV_FIELDS = ["annotation_id", "record_id", "doc_type", "entity_type", "text",
                 "start", "end", "source", "expected_handling", "tags"]


def save_ground_truth(entities: Iterable[PlantedEntity], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [e.to_dict() for e in entities]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)
    logger.info("Saved %d ground-truth annotations", len(data))


def save_ground_truth_csv(entities: Iterable[PlantedEntity], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=GT_CSV_FIELDS)
        w.writeheader()
        for e in entities:
            row = e.to_dict()
            row["tags"] = ";".join(row["tags"])
            w.writerow(row)


def load_ground_truth(path: Path) -> List[PlantedEntity]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Ground-truth file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        PlantedEntity(
            annotation_id=d["annotation_id"], record_id=d["record_id"],
            doc_type=d["doc_type"], entity_type=d["entity_type"], text=d["text"],
            start=int(d["start"]), end=int(d["end"]), source=d.get("source", "planted"),
            expected_handling=d.get("expected_handling", "REDACT"),
            tags=tuple(d.get("tags", ())),
        )
        for d in data
    ]


def save_traps(traps: Iterable[TrapAnnotation], path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [t.to_dict() for t in traps]
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=1, ensure_ascii=False)


def load_traps(path: Path) -> List[TrapAnnotation]:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Trap file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return [
        TrapAnnotation(
            trap_id=d["trap_id"], record_id=d["record_id"], doc_type=d["doc_type"],
            kind=d["kind"], text=d["text"], start=int(d["start"]), end=int(d["end"]),
            expected_handling=d.get("expected_handling", "KEEP"),
            tags=tuple(d.get("tags", ())),
        )
        for d in data
    ]


def validate_annotations(records: List[SyntheticRecord], gt: List[PlantedEntity],
                         traps: List[TrapAnnotation]) -> Dict[str, object]:
    """Check every annotation against its document text.

    Raises ValueError listing the first problems; returns a summary otherwise.
    Checks: record exists, 0 <= start < end <= len(text), text[start:end] equals
    the annotated value, unique annotation/trap ids, entity type in scope,
    traps never overlap a ground-truth span.
    """
    texts = {r.record_id: r.text for r in records}
    problems: List[str] = []
    seen_ids = set()

    def _check_span(kind, item_id, record_id, start, end, value):
        text = texts.get(record_id)
        if text is None:
            problems.append(f"{kind} {item_id}: unknown record")
            return
        if not (0 <= start < end <= len(text)):
            problems.append(f"{kind} {item_id}: invalid span {start}:{end}")
        elif text[start:end] != value:
            problems.append(f"{kind} {item_id}: offset mismatch")

    for e in gt:
        if e.annotation_id in seen_ids:
            problems.append(f"duplicate id {e.annotation_id}")
        seen_ids.add(e.annotation_id)
        if e.entity_type not in ENTITY_TYPES:
            problems.append(f"annotation {e.annotation_id}: out-of-scope type {e.entity_type}")
        _check_span("annotation", e.annotation_id, e.record_id, e.start, e.end, e.text)

    gt_by_rec: Dict[str, List[PlantedEntity]] = {}
    for e in gt:
        gt_by_rec.setdefault(e.record_id, []).append(e)
    for t in traps:
        if t.trap_id in seen_ids:
            problems.append(f"duplicate id {t.trap_id}")
        seen_ids.add(t.trap_id)
        _check_span("trap", t.trap_id, t.record_id, t.start, t.end, t.text)
        for e in gt_by_rec.get(t.record_id, []):
            if t.start < e.end and e.start < t.end:
                problems.append(f"trap {t.trap_id} overlaps {e.annotation_id}")

    if problems:
        raise ValueError(f"{len(problems)} annotation problems, e.g.: " + "; ".join(problems[:5]))
    return {
        "records": len(records),
        "annotations": len(gt),
        "traps": len(traps),
        "entity_types": sorted({e.entity_type for e in gt}),
        "all_offsets_valid": True,
    }
