"""
evaluation.py
-------------
Compare predicted spans with the independent ground truth.

Matching (deterministic, one-to-one, per record)
    GT sorted by (start, end, type); predictions by (start, end, -score, label).
    1. EXACT        same span and same canonical label             -> TP
    2. WRONG_LABEL  same span, different label                      -> GT is FN, prediction is FP
    3. PARTIAL      overlapping, same label (best IoU first)       -> GT is FN, prediction is FP
                    (counted separately for the secondary "overlap recall")
    4. remaining predictions: DUPLICATE if they overlap an already-matched
       prediction of the same label, otherwise SPURIOUS            -> FP
    5. remaining GT: MISSED                                         -> FN
    A prediction can be consumed by at most one GT occurrence. Nested GT
    (e.g. a POSTAL_CODE inside an ADDRESS) are independent targets.

Primary metrics are exact-span, entity-level:
    Recall    = TP / (TP + FN)
    Precision = TP / (TP + FP)
    F1        = 2PR / (P + R)
A zero denominator gives None, written as "N/A" in reports.

Secondary
    overlap_recall          = (exact + partial) / GT
    redaction_coverage      = GT occurrences whose every character is covered by
                              the union of predicted spans (any label) / GT.
                              This is what matters for redaction: a span that is
                              fully replaced is protected even if the label or
                              boundaries differ.
    trap hit rate           = annotated FP traps overlapped by any prediction / traps
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ENTITY_ORDER = ["PERSON", "PHONE_NUMBER", "CNIC", "EMAIL_ADDRESS",
                "ADDRESS", "POSTAL_CODE", "CUSTOMER_ID"]


@dataclass(frozen=True)
class Prediction:
    """A normalised detection (canonical label), independent of Presidio objects."""
    start: int
    end: int
    label: str
    score: float = 1.0
    raw_label: str = ""
    recognizer: str = ""

    def to_dict(self) -> dict:
        return {"start": self.start, "end": self.end, "label": self.label,
                "score": round(float(self.score), 4), "raw_label": self.raw_label,
                "recognizer": self.recognizer}

    @staticmethod
    def from_dict(d: dict) -> "Prediction":
        return Prediction(int(d["start"]), int(d["end"]), d["label"], float(d.get("score", 1.0)),
                          d.get("raw_label", ""), d.get("recognizer", ""))


def _ratio(num: int, den: int) -> Optional[float]:
    return None if den == 0 else num / den


def _f1(p: Optional[float], r: Optional[float]) -> Optional[float]:
    if p is None or r is None:
        return None
    if p + r == 0:
        return 0.0
    return 2 * p * r / (p + r)


def fmt_metric(v: Optional[float]) -> str:
    return "N/A" if v is None else f"{v:.4f}"


@dataclass
class EntityTypeMetrics:
    entity_type: str
    gt_count: int = 0
    pred_count: int = 0
    tp: int = 0
    fn: int = 0
    fp: int = 0
    partial: int = 0
    wrong_label: int = 0
    duplicate: int = 0
    covered: int = 0

    @property
    def recall(self) -> Optional[float]:
        return _ratio(self.tp, self.tp + self.fn)

    @property
    def precision(self) -> Optional[float]:
        return _ratio(self.tp, self.tp + self.fp)

    @property
    def f1(self) -> Optional[float]:
        return _f1(self.precision, self.recall)

    @property
    def overlap_recall(self) -> Optional[float]:
        return _ratio(self.tp + self.partial, self.gt_count)

    @property
    def redaction_coverage(self) -> Optional[float]:
        return _ratio(self.covered, self.gt_count)

    def to_row(self) -> dict:
        return {
            "entity_type": self.entity_type,
            "gt_count": self.gt_count,
            "pred_count": self.pred_count,
            "tp": self.tp, "fn": self.fn, "fp": self.fp,
            "recall": fmt_metric(self.recall),
            "precision": fmt_metric(self.precision),
            "f1": fmt_metric(self.f1),
            "partial": self.partial,
            "wrong_label": self.wrong_label,
            "duplicate": self.duplicate,
            "overlap_recall": fmt_metric(self.overlap_recall),
            "redaction_coverage": fmt_metric(self.redaction_coverage),
        }


@dataclass
class MatchDetail:
    record_id: str
    category: str                 # exact | wrong_label | partial | duplicate | spurious | missed
    annotation_id: str = ""
    gt_type: str = ""
    gt_start: int = -1
    gt_end: int = -1
    pred_label: str = ""
    pred_start: int = -1
    pred_end: int = -1
    pred_score: float = 0.0
    recognizer: str = ""


@dataclass
class EvaluationReport:
    mode: str
    per_type: Dict[str, EntityTypeMetrics]
    overall: EntityTypeMetrics
    per_doc_type: Dict[str, EntityTypeMetrics]
    per_tag: Dict[str, EntityTypeMetrics]
    per_record: Dict[str, EntityTypeMetrics]
    record_doc_type: Dict[str, str]
    details: List[MatchDetail]
    trap_total: int = 0
    trap_hits: int = 0
    trap_hits_by_kind: Dict[str, Tuple[int, int]] = field(default_factory=dict)
    hit_trap_ids: List[str] = field(default_factory=list)
    # GT annotation ids whose characters are NOT all covered by predictions
    # (computed on the original text; complements the value-based residual check)
    uncovered_ids: List[str] = field(default_factory=list)

    @property
    def trap_hit_rate(self) -> Optional[float]:
        return _ratio(self.trap_hits, self.trap_total)

    def false_negatives(self) -> List[MatchDetail]:
        """GT occurrences not matched exactly (missed, partial, wrong_label)."""
        return [d for d in self.details if d.annotation_id and d.category != "exact"]

    def false_positives(self) -> List[MatchDetail]:
        return [d for d in self.details if d.pred_label and d.category != "exact"]


def _overlap(a0: int, a1: int, b0: int, b1: int) -> int:
    return max(0, min(a1, b1) - max(a0, b0))


def match_record(record_id: str, gt: Sequence, preds: Sequence[Prediction]) -> List[MatchDetail]:
    """Deterministic one-to-one matching for one record (see module docstring)."""
    gts = sorted(gt, key=lambda g: (g.start, g.end, g.entity_type, g.annotation_id))
    ps = sorted(preds, key=lambda p: (p.start, p.end, -p.score, p.label, p.recognizer))
    g_used: Dict[int, MatchDetail] = {}
    p_used: Dict[int, str] = {}
    details: List[MatchDetail] = []

    def _detail(cat, gi=None, pi=None):
        d = MatchDetail(record_id=record_id, category=cat)
        if gi is not None:
            g = gts[gi]
            d.annotation_id, d.gt_type, d.gt_start, d.gt_end = g.annotation_id, g.entity_type, g.start, g.end
        if pi is not None:
            p = ps[pi]
            d.pred_label, d.pred_start, d.pred_end = p.label, p.start, p.end
            d.pred_score, d.recognizer = p.score, p.recognizer
        return d

    # 1. exact
    for gi, g in enumerate(gts):
        for pi, p in enumerate(ps):
            if pi in p_used:
                continue
            if p.start == g.start and p.end == g.end and p.label == g.entity_type:
                d = _detail("exact", gi, pi)
                g_used[gi] = d
                p_used[pi] = "exact"
                details.append(d)
                break
    # 2. wrong label (same span)
    for gi, g in enumerate(gts):
        if gi in g_used:
            continue
        for pi, p in enumerate(ps):
            if pi in p_used:
                continue
            if p.start == g.start and p.end == g.end:
                d = _detail("wrong_label", gi, pi)
                g_used[gi] = d
                p_used[pi] = "wrong_label"
                details.append(d)
                break
    # 3. partial (same label, overlapping), best IoU first
    cands = []
    for gi, g in enumerate(gts):
        if gi in g_used:
            continue
        for pi, p in enumerate(ps):
            if pi in p_used or p.label != g.entity_type:
                continue
            inter = _overlap(g.start, g.end, p.start, p.end)
            if inter > 0:
                union = max(g.end, p.end) - min(g.start, p.start)
                cands.append((-inter / union, gi, pi))
    for _neg_iou, gi, pi in sorted(cands):
        if gi in g_used or pi in p_used:
            continue
        d = _detail("partial", gi, pi)
        g_used[gi] = d
        p_used[pi] = "partial"
        details.append(d)
    # 4. leftover predictions
    for pi, p in enumerate(ps):
        if pi in p_used:
            continue
        dup = any(
            cat in ("exact", "partial", "wrong_label") and ps[qi].label == p.label
            and _overlap(p.start, p.end, ps[qi].start, ps[qi].end) > 0
            for qi, cat in p_used.items()
        )
        details.append(_detail("duplicate" if dup else "spurious", None, pi))
        p_used[pi] = "duplicate" if dup else "spurious"
    # 5. leftover GT
    for gi in range(len(gts)):
        if gi not in g_used:
            details.append(_detail("missed", gi, None))
    return details


def _covered(g, preds: Sequence[Prediction]) -> bool:
    """True if every character of g is inside the union of predicted spans."""
    pos = g.start
    for p in sorted(preds, key=lambda x: (x.start, x.end)):
        if p.start <= pos < p.end:
            pos = p.end
            if pos >= g.end:
                return True
    return pos >= g.end


def evaluate(ground_truth: Iterable, predictions_by_record: Dict[str, List[Prediction]],
             traps: Optional[Iterable] = None, doc_types: Optional[Dict[str, str]] = None,
             mode: str = "unknown") -> EvaluationReport:
    """Evaluate predictions against ground truth for all records.

    ``doc_types`` maps record_id -> doc_type and defines the record universe
    (records without GT still count their FPs). If omitted, the union of
    records in GT and predictions is used.
    """
    gt_by_rec: Dict[str, list] = defaultdict(list)
    for g in ground_truth:
        gt_by_rec[g.record_id].append(g)
    if doc_types is None:
        doc_types = {}
        for rid, gl in gt_by_rec.items():
            doc_types[rid] = gl[0].doc_type
        for rid in predictions_by_record:
            doc_types.setdefault(rid, "unknown")

    per_type = {t: EntityTypeMetrics(t) for t in ENTITY_ORDER}
    overall = EntityTypeMetrics("OVERALL")
    per_doc: Dict[str, EntityTypeMetrics] = {}
    per_tag: Dict[str, EntityTypeMetrics] = {}
    per_record: Dict[str, EntityTypeMetrics] = {}
    details_all: List[MatchDetail] = []
    uncovered: List[str] = []

    def _bucket(d: Dict[str, EntityTypeMetrics], key: str) -> EntityTypeMetrics:
        if key not in d:
            d[key] = EntityTypeMetrics(key)
        return d[key]

    for rid in sorted(doc_types):
        gts = gt_by_rec.get(rid, [])
        preds = predictions_by_record.get(rid, [])
        dt = doc_types[rid]
        details = match_record(rid, gts, preds)
        details_all.extend(details)
        gt_index = {g.annotation_id: g for g in gts}
        rec_m = _bucket(per_record, rid)
        doc_m = _bucket(per_doc, dt)

        for g in gts:
            cov = _covered(g, preds)
            if not cov:
                uncovered.append(g.annotation_id)
            for m in (per_type.setdefault(g.entity_type, EntityTypeMetrics(g.entity_type)),
                      overall, rec_m, doc_m):
                m.gt_count += 1
                m.covered += int(cov)
            for tag in g.tags:
                tm = _bucket(per_tag, tag)
                tm.gt_count += 1
                tm.covered += int(cov)
        for p in preds:
            for m in (per_type.setdefault(p.label, EntityTypeMetrics(p.label)), overall, rec_m, doc_m):
                m.pred_count += 1

        for d in details:
            targets_gt = []
            if d.annotation_id:
                g = gt_index[d.annotation_id]
                targets_gt = [per_type[g.entity_type], overall, rec_m, doc_m] + \
                             [_bucket(per_tag, t) for t in g.tags]
            targets_pred = []
            if d.pred_label:
                targets_pred = [per_type.setdefault(d.pred_label, EntityTypeMetrics(d.pred_label)),
                                overall, rec_m, doc_m]
            if d.category == "exact":
                for m in targets_gt:
                    m.tp += 1
                # tag buckets have no FP notion; TP counted once above
                continue
            for m in targets_gt:
                m.fn += 1
                if d.category == "partial":
                    m.partial += 1
                elif d.category == "wrong_label":
                    m.wrong_label += 1
            for m in targets_pred:
                m.fp += 1
                if d.category == "duplicate":
                    m.duplicate += 1

    report = EvaluationReport(mode=mode, per_type=per_type, overall=overall, per_doc_type=per_doc,
                              per_tag=per_tag, per_record=per_record, record_doc_type=dict(doc_types),
                              details=details_all, uncovered_ids=uncovered)

    if traps is not None:
        by_kind: Dict[str, List[int]] = defaultdict(lambda: [0, 0])
        hits: List[str] = []
        for t in traps:
            preds = predictions_by_record.get(t.record_id, [])
            hit = any(_overlap(t.start, t.end, p.start, p.end) > 0 for p in preds)
            by_kind[t.kind][1] += 1
            report.trap_total += 1
            if hit:
                by_kind[t.kind][0] += 1
                report.trap_hits += 1
                hits.append(t.trap_id)
        report.trap_hits_by_kind = {k: (v[0], v[1]) for k, v in sorted(by_kind.items())}
        report.hit_trap_ids = hits
    return report


def per_document_rows(report: EvaluationReport) -> List[dict]:
    rows = []
    for rid in sorted(report.per_record):
        m = report.per_record[rid]
        rows.append({
            "mode": report.mode, "record_id": rid, "doc_type": report.record_doc_type.get(rid, ""),
            "gt_count": m.gt_count, "pred_count": m.pred_count, "tp": m.tp, "fn": m.fn,
            "fp": m.fp, "partial": m.partial, "wrong_label": m.wrong_label,
            "all_gt_exact": m.fn == 0, "all_gt_covered": m.covered == m.gt_count,
        })
    return rows


def format_summary(report: EvaluationReport) -> str:
    lines = [f"Evaluation summary - {report.mode} (exact-span, entity-level)",
             f"{'Entity':<15}{'GT':>6}{'Pred':>6}{'TP':>6}{'FN':>6}{'FP':>6}"
             f"{'Recall':>9}{'Prec.':>9}{'F1':>9}"]
    rows = [m for m in report.per_type.values() if m.gt_count or m.pred_count] + [report.overall]
    for m in rows:
        lines.append(f"{m.entity_type:<15}{m.gt_count:>6}{m.pred_count:>6}{m.tp:>6}{m.fn:>6}{m.fp:>6}"
                     f"{fmt_metric(m.recall):>9}{fmt_metric(m.precision):>9}{fmt_metric(m.f1):>9}")
    if report.trap_total:
        lines.append(f"FP traps hit: {report.trap_hits}/{report.trap_total} "
                     f"({fmt_metric(report.trap_hit_rate)})")
    return "\n".join(lines)
