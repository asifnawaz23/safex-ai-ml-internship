"""
pipeline.py
-----------
Orchestration shared by the CLI, scripts and tests:

    generate_and_save()  -> data/generated/* (documents, ground truth, traps, manifest)
    load_dataset()       -> validated records, ground truth, traps
    run_experiment()     -> analyse + normalise + redact + residual check for one mode
    save_experiment()    -> output/predictions/{mode}_predictions.json  (spans only, no text)
                            output/predictions/{mode}_residuals.json    (masked values)
                            output/redacted/{mode}_redacted.jsonl       (redacted text)
                            output/metrics/{mode}_engine.json           (engine metadata + runtime)
    load_predictions()   -> predictions per record for evaluation

Originals (data/generated), annotations (data/generated) and redacted output
(output/redacted) live in separate trees; ``save_experiment`` checks this.
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from pii_pipeline import config
from pii_pipeline.evaluation import Prediction
from pii_pipeline.ground_truth import (
    load_ground_truth, load_traps, save_ground_truth, save_ground_truth_csv,
    save_traps, validate_annotations,
)
from pii_pipeline.privacy import (
    PrivacyGuardError, assert_synthetic_rows, ensure_within,
    validate_document_text, validate_output_dir_separation,
)
from pii_pipeline.synthetic_data import (
    GENERATOR_VERSION, PlantedEntity, SyntheticRecord, TrapAnnotation,
    generate_dataset_full,
)

logger = logging.getLogger(__name__)

DOC_FIELDS = ["record_id", "doc_type", "source", "synthetic", "text"]


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _display_path(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(config.ROOT)).replace("\\", "/")
    except ValueError:
        return Path(p).name


def data_dir() -> Path:
    return config.get_path("dataset.output_dir")


# ---------------------------------------------------------------------------
# Dataset
# ---------------------------------------------------------------------------

def save_documents_csv(records: List[SyntheticRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=DOC_FIELDS)
        w.writeheader()
        for r in records:
            row = r.to_dict()
            row["synthetic"] = "true" if r.synthetic else "false"
            w.writerow(row)


def generate_and_save(seed: int = None, count: int = None, out_dir: Optional[Path] = None) -> dict:
    """Generate the dataset, validate it and write all files. Returns the manifest."""
    seed = config.SEED if seed is None else seed
    count = config.RECORD_COUNT if count is None else count
    # out_dir is only overridden programmatically (tests use a temp dir);
    # the CLI always writes to data/generated.
    out_dir = Path(out_dir) if out_dir else data_dir()

    records, gt, traps = generate_dataset_full(seed=seed, count=count)
    summary = validate_annotations(records, gt, traps)
    if len({r.record_id for r in records}) != len(records) or len({r.text for r in records}) != len(records):
        raise RuntimeError("Generated records are not unique")

    files = {
        "documents": out_dir / config.get("dataset.documents_file"),
        "ground_truth_json": out_dir / config.get("dataset.ground_truth_file"),
        "ground_truth_csv": out_dir / config.get("dataset.annotations_csv"),
        "fp_traps": out_dir / config.get("dataset.traps_file"),
    }
    save_documents_csv(records, files["documents"])
    save_ground_truth(gt, files["ground_truth_json"])
    save_ground_truth_csv(gt, files["ground_truth_csv"])
    save_traps(traps, files["fp_traps"])

    def _count(items, key):
        out: Dict[str, int] = {}
        for it in items:
            k = getattr(it, key)
            out[k] = out.get(k, 0) + 1
        return dict(sorted(out.items()))

    manifest = {
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "requested_count": count,
        "total_records": len(records),
        "planted_records": sum(1 for r in records if r.source == "planted"),
        "challenge_records": sum(1 for r in records if r.source == "challenge"),
        "records_without_pii": sum(1 for r in records if not r.planted_entities),
        "annotations": len(gt),
        "traps": len(traps),
        "entity_type_counts": _count(gt, "entity_type"),
        "doc_type_counts": _count(records, "doc_type"),
        "trap_kind_counts": _count(traps, "kind"),
        "all_offsets_valid": summary["all_offsets_valid"],
        "offset_convention": "0-based, end-exclusive",
        "synthetic_only": True,
        "files": {k: {"path": _display_path(p), "sha256": _sha256(p)} for k, p in files.items()},
    }
    manifest_path = out_dir / config.get("dataset.manifest_file")
    with open(manifest_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=2)
    logger.info("Dataset written: %d records, %d annotations, %d traps",
                len(records), len(gt), len(traps))
    return manifest


def load_dataset(in_dir: Optional[Path] = None
                 ) -> Tuple[List[SyntheticRecord], List[PlantedEntity], List[TrapAnnotation]]:
    """Load and validate the generated dataset (refuses non-synthetic files)."""
    in_dir = Path(in_dir) if in_dir else data_dir()
    ensure_within(in_dir, config.ROOT / "data")
    doc_path = in_dir / config.get("dataset.documents_file")
    if not doc_path.exists():
        raise FileNotFoundError("Dataset not found. Run: python -m pii_pipeline.cli generate")
    with open(doc_path, "r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    if not rows or "synthetic" not in rows[0]:
        raise PrivacyGuardError("Documents file has no 'synthetic' column; refusing to process")
    assert_synthetic_rows(rows)
    gt = load_ground_truth(in_dir / config.get("dataset.ground_truth_file"))
    traps = load_traps(in_dir / config.get("dataset.traps_file"))
    gt_by: Dict[str, List[PlantedEntity]] = {}
    for g in gt:
        gt_by.setdefault(g.record_id, []).append(g)
    tr_by: Dict[str, List[TrapAnnotation]] = {}
    for t in traps:
        tr_by.setdefault(t.record_id, []).append(t)
    records = []
    for row in rows:
        validate_document_text(row["text"])
        records.append(SyntheticRecord(row["record_id"], row["doc_type"], row["text"],
                                       row.get("source", "planted"), True,
                                       gt_by.get(row["record_id"], []), tr_by.get(row["record_id"], [])))
    validate_annotations(records, gt, traps)
    return records, gt, traps


# ---------------------------------------------------------------------------
# Experiments
# ---------------------------------------------------------------------------

@dataclass
class ExperimentResult:
    mode: str
    engine_meta: dict
    predictions: Dict[str, List[Prediction]]
    redacted: Dict[str, str]
    residuals: List[dict]
    runtime_seconds: float
    engine_build_seconds: float
    record_count: int
    char_count: int
    doc_types: Dict[str, str] = field(default_factory=dict)


def run_experiment(mode: str, records: List[SyntheticRecord], gt: List[PlantedEntity]) -> ExperimentResult:
    from pii_pipeline.analyzer import analyze_text, build_analyzer, describe_engine
    from pii_pipeline.redactor import find_residuals, redact_text

    t0 = time.perf_counter()
    engine = build_analyzer(mode)
    build_s = time.perf_counter() - t0
    gt_by: Dict[str, List[PlantedEntity]] = {}
    for g in gt:
        gt_by.setdefault(g.record_id, []).append(g)

    preds: Dict[str, List[Prediction]] = {}
    redacted: Dict[str, str] = {}
    residuals: List[dict] = []
    t1 = time.perf_counter()
    for i, rec in enumerate(records, 1):
        p = analyze_text(engine, rec.text, mode)
        preds[rec.record_id] = p
        red = redact_text(rec.text, p, rec.record_id)
        redacted[rec.record_id] = red.text
        for r in find_residuals(red.text, gt_by.get(rec.record_id, [])):
            residuals.append(r.__dict__.copy())
        if i % 200 == 0:
            logger.info("%s: %d/%d records analysed", mode, i, len(records))
    runtime = time.perf_counter() - t1
    logger.info("%s: done, %d records, %d detections, %d residual values",
                mode, len(records), sum(len(v) for v in preds.values()), len(residuals))
    return ExperimentResult(mode, describe_engine(engine, mode), preds, redacted, residuals,
                            runtime, build_s, len(records), sum(len(r.text) for r in records),
                            {r.record_id: r.doc_type for r in records})


def predictions_path(mode: str) -> Path:
    return config.get_path("output.predictions_dir") / f"{mode}_predictions.json"


def residuals_path(mode: str) -> Path:
    return config.get_path("output.predictions_dir") / f"{mode}_residuals.json"


def redacted_path(mode: str) -> Path:
    return config.get_path("output.redacted_dir") / f"{mode}_redacted.jsonl"


def engine_meta_path(mode: str) -> Path:
    return config.get_path("output.metrics_dir") / f"{mode}_engine.json"


def save_experiment(result: ExperimentResult) -> Dict[str, Path]:
    validate_output_dir_separation(data_dir(), data_dir(), config.get_path("output.redacted_dir"))
    paths = {"predictions": predictions_path(result.mode), "residuals": residuals_path(result.mode),
             "redacted": redacted_path(result.mode), "engine": engine_meta_path(result.mode)}
    for p in paths.values():
        ensure_within(p, config.ROOT / "output").parent.mkdir(parents=True, exist_ok=True)

    with open(paths["predictions"], "w", encoding="utf-8", newline="\n") as f:
        json.dump({"mode": result.mode,
                   "predictions": {rid: [p.to_dict() for p in ps] for rid, ps in result.predictions.items()}},
                  f, indent=None, separators=(",", ":"))
    with open(paths["residuals"], "w", encoding="utf-8", newline="\n") as f:
        json.dump({"mode": result.mode, "residuals": result.residuals}, f, indent=1)
    with open(paths["redacted"], "w", encoding="utf-8", newline="\n") as f:
        for rid, text in result.redacted.items():
            f.write(json.dumps({"record_id": rid, "doc_type": result.doc_types.get(rid, ""),
                                "redacted_text": text}, ensure_ascii=False) + "\n")
    meta = dict(result.engine_meta)
    meta.update({"records": result.record_count, "characters": result.char_count,
                 "runtime_seconds": round(result.runtime_seconds, 3),
                 "engine_build_seconds": round(result.engine_build_seconds, 3),
                 "ms_per_record": round(1000 * result.runtime_seconds / max(1, result.record_count), 2)})
    with open(paths["engine"], "w", encoding="utf-8", newline="\n") as f:
        json.dump(meta, f, indent=2)
    return paths


def load_predictions(mode: str) -> Dict[str, List[Prediction]]:
    path = predictions_path(mode)
    if not path.exists():
        raise FileNotFoundError(f"No saved {mode} predictions. Run: python -m pii_pipeline.cli {mode}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {rid: [Prediction.from_dict(d) for d in ps] for rid, ps in data["predictions"].items()}


def load_residuals(mode: str) -> List[dict]:
    path = residuals_path(mode)
    if not path.exists():
        raise FileNotFoundError(f"No saved {mode} residuals. Run: python -m pii_pipeline.cli {mode}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)["residuals"]


def load_engine_meta(mode: str) -> dict:
    path = engine_meta_path(mode)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
