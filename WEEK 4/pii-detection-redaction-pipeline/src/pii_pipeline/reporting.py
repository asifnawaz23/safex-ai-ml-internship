"""
reporting.py
------------
Writes evaluation tables (CSV/JSON) and charts (PNG) from EvaluationReport
objects. Reports are always rebuilt from saved predictions + ground truth,
never by parsing previously written CSVs.

output/metrics/
    baseline_metrics.csv, improved_metrics.csv   per entity type + OVERALL
    comparison.csv                               baseline vs improved per entity type + OVERALL, targets
    experiment_summary.csv                       dataset size, runtime, trap rate, residuals per mode
    per_document_metrics.csv                     per record, both modes
    doc_type_metrics.csv                         per document type, both modes
    edge_case_metrics.csv                        recall per edge-case tag, both modes
    fp_trap_report.csv                           trap hits per trap kind, both modes
    residual_pii_report.csv                      residual planted values per mode x entity type,
                                                 plus not-fully-redacted / partial-leak counts
    residual_pii_details.csv                     one row per residual occurrence (masked value)
    summary.json                                 machine-readable summary of the above
output/charts/
    recall_by_entity.png, precision_recall_comparison.png
"""

from __future__ import annotations

import csv
import json
import logging
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import matplotlib
matplotlib.use("Agg")  # headless
import matplotlib.pyplot as plt  # noqa: E402

from pii_pipeline import config  # noqa: E402
from pii_pipeline.evaluation import (  # noqa: E402
    ENTITY_ORDER, EntityTypeMetrics, EvaluationReport, fmt_metric, per_document_rows,
)

logger = logging.getLogger(__name__)

DIRECT_IDENTIFIERS = ("PHONE_NUMBER", "CNIC", "EMAIL_ADDRESS")


def metrics_dir() -> Path:
    p = config.get_path("output.metrics_dir")
    p.mkdir(parents=True, exist_ok=True)
    return p


def charts_dir() -> Path:
    p = config.get_path("output.charts_dir")
    p.mkdir(parents=True, exist_ok=True)
    return p


def write_csv(rows: List[dict], path: Path, fieldnames: Optional[List[str]] = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    return path


def metrics_rows(report: EvaluationReport) -> List[dict]:
    rows = [report.per_type[t].to_row() for t in ENTITY_ORDER if t in report.per_type]
    rows.append(report.overall.to_row())
    return rows


def _num(v: Optional[float]) -> Optional[float]:
    return None if v is None else round(v, 4)


def _delta(a: Optional[float], b: Optional[float]) -> str:
    if a is None or b is None:
        return "N/A"
    return f"{b - a:+.4f}"


def _meets(v: Optional[float], target: Optional[float]) -> str:
    if target is None:
        return ""
    if v is None:
        return "N/A"
    return "yes" if v >= target else "no"


def comparison_rows(base: EvaluationReport, imp: EvaluationReport) -> List[dict]:
    rec_t = config.get("targets.recall", {})
    prec_t = config.get("targets.precision", {})
    rows = []
    for t in ENTITY_ORDER + ["OVERALL"]:
        b = base.overall if t == "OVERALL" else base.per_type.get(t, EntityTypeMetrics(t))
        i = imp.overall if t == "OVERALL" else imp.per_type.get(t, EntityTypeMetrics(t))
        tr = config.get("targets.overall_recall") if t == "OVERALL" else rec_t.get(t)
        tp_ = None if t == "OVERALL" else prec_t.get(t)
        rows.append({
            "entity_type": t, "gt_count": i.gt_count,
            "baseline_tp": b.tp, "baseline_fn": b.fn, "baseline_fp": b.fp,
            "baseline_recall": fmt_metric(b.recall), "baseline_precision": fmt_metric(b.precision),
            "baseline_f1": fmt_metric(b.f1), "baseline_overlap_recall": fmt_metric(b.overlap_recall),
            "baseline_redaction_coverage": fmt_metric(b.redaction_coverage),
            "improved_tp": i.tp, "improved_fn": i.fn, "improved_fp": i.fp,
            "improved_recall": fmt_metric(i.recall), "improved_precision": fmt_metric(i.precision),
            "improved_f1": fmt_metric(i.f1), "improved_overlap_recall": fmt_metric(i.overlap_recall),
            "improved_redaction_coverage": fmt_metric(i.redaction_coverage),
            "delta_recall": _delta(b.recall, i.recall), "delta_precision": _delta(b.precision, i.precision),
            "delta_f1": _delta(b.f1, i.f1),
            "target_recall": "" if tr is None else tr, "target_precision": "" if tp_ is None else tp_,
            "improved_meets_recall_target": _meets(i.recall, tr),
            "improved_meets_precision_target": _meets(i.precision, tp_),
        })
    return rows


def residual_summary_rows(mode: str, residuals: List[dict], gt,
                          report: Optional[EvaluationReport] = None) -> List[dict]:
    """Residual summary per entity type.

    residual_count       whole planted values found in the redacted text
                         (redactor.find_residuals, value matching).
    not_fully_redacted   planted occurrences with at least one character not
                         covered by any prediction (original-text offsets;
                         = gt_count - covered, the complement of redaction_coverage).
    partial_leaks_not_value_matched
                         not_fully_redacted occurrences that the whole-value
                         check does NOT report, i.e. a fragment survives
                         (e.g. house number + street of an address). This is the
                         part of the exposure that residual_count under-reports.
    The last two columns need the evaluation report; they are empty without it.
    """
    gt_counts = Counter(g.entity_type for g in gt)
    res = Counter(r["entity_type"] for r in residuals)
    exact = Counter(r["entity_type"] for r in residuals if r["match_kind"] == "exact")
    not_full: Counter = Counter()
    partial_only: Counter = Counter()
    if report is not None:
        type_of = {g.annotation_id: g.entity_type for g in gt}
        residual_ids = {r["annotation_id"] for r in residuals}
        for aid in report.uncovered_ids:
            t = type_of.get(aid)
            not_full[t] += 1
            if aid not in residual_ids:
                partial_only[t] += 1

    def _opt(counter: Counter, key=None):
        if report is None:
            return ""
        return sum(counter.values()) if key is None else counter.get(key, 0)

    rows = []
    for t in ENTITY_ORDER:
        n = gt_counts.get(t, 0)
        rows.append({"mode": mode, "entity_type": t, "gt_count": n, "residual_count": res.get(t, 0),
                     "residual_rate": fmt_metric(None if n == 0 else res.get(t, 0) / n),
                     "exact_value_matches": exact.get(t, 0),
                     "digit_sequence_matches": res.get(t, 0) - exact.get(t, 0),
                     "not_fully_redacted": _opt(not_full, t),
                     "partial_leaks_not_value_matched": _opt(partial_only, t)})
    total = sum(gt_counts.values())
    rows.append({"mode": mode, "entity_type": "OVERALL", "gt_count": total,
                 "residual_count": len(residuals),
                 "residual_rate": fmt_metric(None if total == 0 else len(residuals) / total),
                 "exact_value_matches": sum(exact.values()),
                 "digit_sequence_matches": len(residuals) - sum(exact.values()),
                 "not_fully_redacted": _opt(not_full),
                 "partial_leaks_not_value_matched": _opt(partial_only)})
    return rows


def _direct_residual_rate(residuals: List[dict], gt) -> Optional[float]:
    n = sum(1 for g in gt if g.entity_type in DIRECT_IDENTIFIERS)
    r = sum(1 for x in residuals if x["entity_type"] in DIRECT_IDENTIFIERS)
    return None if n == 0 else r / n


def write_all_metrics(reports: Dict[str, EvaluationReport], residuals: Dict[str, List[dict]],
                      engine_meta: Dict[str, dict], gt, manifest: Optional[dict] = None,
                      out_dir: Optional[Path] = None) -> Dict[str, Path]:
    md = Path(out_dir) if out_dir else metrics_dir()
    md.mkdir(parents=True, exist_ok=True)
    out: Dict[str, Path] = {}
    for mode, rep in reports.items():
        out[f"{mode}_metrics"] = write_csv(metrics_rows(rep), md / f"{mode}_metrics.csv")
    base, imp = reports["baseline"], reports["improved"]
    out["comparison"] = write_csv(comparison_rows(base, imp), md / "comparison.csv")

    per_doc = per_document_rows(base) + per_document_rows(imp)
    out["per_document"] = write_csv(per_doc, md / "per_document_metrics.csv")

    doc_rows, tag_rows, trap_rows, res_rows, res_detail = [], [], [], [], []
    for mode, rep in reports.items():
        for dt in sorted(rep.per_doc_type):
            m = rep.per_doc_type[dt]
            doc_rows.append({"mode": mode, "doc_type": dt, "gt_count": m.gt_count, "pred_count": m.pred_count,
                             "tp": m.tp, "fn": m.fn, "fp": m.fp, "recall": fmt_metric(m.recall),
                             "precision": fmt_metric(m.precision), "f1": fmt_metric(m.f1),
                             "redaction_coverage": fmt_metric(m.redaction_coverage)})
        for tag in sorted(rep.per_tag):
            m = rep.per_tag[tag]
            tag_rows.append({"mode": mode, "tag": tag, "gt_count": m.gt_count, "tp": m.tp, "fn": m.fn,
                             "partial": m.partial, "wrong_label": m.wrong_label,
                             "recall": fmt_metric(m.recall), "overlap_recall": fmt_metric(m.overlap_recall),
                             "redaction_coverage": fmt_metric(m.redaction_coverage)})
        for kind, (hits, total) in rep.trap_hits_by_kind.items():
            trap_rows.append({"mode": mode, "trap_kind": kind, "traps": total, "hits": hits,
                              "hit_rate": fmt_metric(None if total == 0 else hits / total)})
        trap_rows.append({"mode": mode, "trap_kind": "ALL", "traps": rep.trap_total, "hits": rep.trap_hits,
                          "hit_rate": fmt_metric(rep.trap_hit_rate)})
        res_rows += residual_summary_rows(mode, residuals.get(mode, []), gt, rep)
        for r in residuals.get(mode, []):
            res_detail.append({"mode": mode, **r})
    out["doc_type"] = write_csv(doc_rows, md / "doc_type_metrics.csv")
    out["edge_case"] = write_csv(tag_rows, md / "edge_case_metrics.csv")
    out["fp_traps"] = write_csv(trap_rows, md / "fp_trap_report.csv")
    out["residual"] = write_csv(res_rows, md / "residual_pii_report.csv")
    out["residual_details"] = write_csv(
        res_detail, md / "residual_pii_details.csv",
        ["mode", "record_id", "annotation_id", "entity_type", "masked_value", "match_kind"])

    summ_rows = []
    summary = {"dataset": manifest or {}, "modes": {}}
    for mode, rep in reports.items():
        meta = engine_meta.get(mode, {})
        res = residuals.get(mode, [])
        s = {
            "records": meta.get("records"), "characters": meta.get("characters"),
            "runtime_seconds": meta.get("runtime_seconds"), "ms_per_record": meta.get("ms_per_record"),
            "engine_build_seconds": meta.get("engine_build_seconds"),
            "overall_recall": _num(rep.overall.recall), "overall_precision": _num(rep.overall.precision),
            "overall_f1": _num(rep.overall.f1), "overall_redaction_coverage": _num(rep.overall.redaction_coverage),
            "gt_occurrences": rep.overall.gt_count, "predictions": rep.overall.pred_count,
            "tp": rep.overall.tp, "fn": rep.overall.fn, "fp": rep.overall.fp,
            "fp_traps": rep.trap_total, "fp_trap_hits": rep.trap_hits, "fp_trap_hit_rate": _num(rep.trap_hit_rate),
            "residual_values": len(res), "residual_direct_identifier_rate": _num(_direct_residual_rate(res, gt)),
            "nlp_model": meta.get("nlp_model"), "presidio_analyzer_version": meta.get("presidio_analyzer_version"),
            "recognizers": meta.get("recognizers"),
        }
        summary["modes"][mode] = s
        for k in ("records", "characters", "runtime_seconds", "ms_per_record", "engine_build_seconds",
                  "gt_occurrences", "predictions", "tp", "fn", "fp", "overall_recall", "overall_precision",
                  "overall_f1", "overall_redaction_coverage", "fp_traps", "fp_trap_hits", "fp_trap_hit_rate",
                  "residual_values", "residual_direct_identifier_rate"):
            summ_rows.append((mode, k, s[k]))
    keys = []
    for _m, k, _v in summ_rows:
        if k not in keys:
            keys.append(k)
    table = [{"metric": k,
              "baseline": next((v for m, kk, v in summ_rows if m == "baseline" and kk == k), ""),
              "improved": next((v for m, kk, v in summ_rows if m == "improved" and kk == k), "")}
             for k in keys]
    for row in table:
        for col in ("baseline", "improved"):
            if row[col] is None:
                row[col] = "N/A"
    out["experiment_summary"] = write_csv(table, md / "experiment_summary.csv", ["metric", "baseline", "improved"])
    summary["targets"] = config.get("targets")
    with open(md / "summary.json", "w", encoding="utf-8", newline="\n") as f:
        json.dump(summary, f, indent=2)
    out["summary"] = md / "summary.json"
    return out


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _val(v: Optional[float]) -> float:
    return 0.0 if v is None else float(v)


def plot_recall_by_entity(base: EvaluationReport, imp: EvaluationReport, path: Optional[Path] = None) -> Path:
    path = path or charts_dir() / "recall_by_entity.png"
    types = [t for t in ENTITY_ORDER if imp.per_type.get(t) and imp.per_type[t].gt_count > 0]
    b = [_val(base.per_type[t].recall) for t in types]
    i = [_val(imp.per_type[t].recall) for t in types]
    targets = config.get("targets.recall", {})
    x = range(len(types))
    w = 0.38
    fig, ax = plt.subplots(figsize=(11, 5.5))
    bb = ax.bar([k - w / 2 for k in x], b, w, label="Baseline (default Presidio)", color="#90A4AE")
    ib = ax.bar([k + w / 2 for k in x], i, w, label="Improved (custom recognisers)", color="#1565C0")
    for k, t in enumerate(types):
        if t in targets:
            ax.hlines(targets[t], k - 0.45, k + 0.45, colors="#D32F2F", linestyles="--", linewidth=1.4,
                      label="Recall target (improved)" if k == 0 else None)
    for bars in (bb, ib):
        for r in bars:
            ax.text(r.get_x() + r.get_width() / 2, r.get_height() + 0.01, f"{r.get_height():.2f}",
                    ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(x))
    ax.set_xticklabels(types, rotation=20, ha="right")
    ax.set_ylim(0, 1.12)
    ax.set_ylabel("Recall (exact span)")
    n = imp.overall.gt_count
    ax.set_title(f"Recall by entity type - baseline vs improved ({n} planted PII occurrences)")
    ax.legend(loc="upper left", fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path


def plot_precision_recall_comparison(base: EvaluationReport, imp: EvaluationReport,
                                     path: Optional[Path] = None) -> Path:
    path = path or charts_dir() / "precision_recall_comparison.png"
    types = [t for t in ENTITY_ORDER if imp.per_type.get(t) and imp.per_type[t].gt_count > 0] + ["OVERALL"]

    def _m(rep, t):
        return rep.overall if t == "OVERALL" else rep.per_type[t]

    fig, axes = plt.subplots(1, 2, figsize=(14, 5.5), sharey=True)
    for ax, metric in zip(axes, ("precision", "recall")):
        x = range(len(types))
        w = 0.38
        for off, rep, color, name in ((-w / 2, base, "#90A4AE", "Baseline"), (w / 2, imp, "#1565C0", "Improved")):
            vals = [getattr(_m(rep, t), metric) for t in types]
            bars = ax.bar([k + off for k in x], [_val(v) for v in vals], w, color=color, label=name)
            for r, v in zip(bars, vals):
                ax.text(r.get_x() + r.get_width() / 2, _val(v) + 0.01, "N/A" if v is None else f"{v:.2f}",
                        ha="center", va="bottom", fontsize=7)
        ax.set_xticks(list(x))
        ax.set_xticklabels(types, rotation=25, ha="right", fontsize=8)
        ax.set_ylim(0, 1.12)
        ax.set_title(metric.capitalize() + " (exact span)")
        ax.legend(fontsize=8, loc="upper left")
    fig.suptitle("Precision and recall: default Presidio vs improved pipeline (N/A = no predictions)")
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)
    return path
