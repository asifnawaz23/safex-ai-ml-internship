"""
Baseline + improved integration on a generated subset (brief test area 18).
Runs the real Presidio engines end to end in memory and writes reports to a
temporary directory (never to output/).
"""
import csv

import pytest

from pii_pipeline import pipeline
from pii_pipeline.evaluation import evaluate
from pii_pipeline.reporting import (
    plot_precision_recall_comparison, plot_recall_by_entity, write_all_metrics,
)

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def runs(small_dataset):
    records, gt, traps = small_dataset
    doc_types = {r.record_id: r.doc_type for r in records}
    out = {}
    for mode in ("baseline", "improved"):
        res = pipeline.run_experiment(mode, records, gt)
        out[mode] = (res, evaluate(gt, res.predictions, traps, doc_types, mode))
    return records, gt, traps, out


def test_both_modes_process_every_record(runs):
    records, _gt, _traps, out = runs
    for mode, (res, rep) in out.items():
        assert set(res.predictions) == {r.record_id for r in records}
        assert set(res.redacted) == {r.record_id for r in records}
        assert rep.overall.gt_count == sum(len(r.planted_entities) for r in records)


def test_engine_metadata_recorded(runs):
    _r, _g, _t, out = runs
    base_meta, imp_meta = out["baseline"][0].engine_meta, out["improved"][0].engine_meta
    assert base_meta["nlp_model"] == imp_meta["nlp_model"] == "en_core_web_sm"
    assert base_meta["presidio_analyzer_version"] == "2.2.364"
    assert "PakistaniCNICRecognizer" not in base_meta["recognizers"]
    assert "PakistaniCNICRecognizer" in imp_meta["recognizers"]
    assert "CNIC" not in base_meta["supported_entities"]     # verified: no default CNIC recogniser


def test_improved_beats_baseline_on_local_identifiers(runs):
    _r, _g, _t, out = runs
    base, imp = out["baseline"][1], out["improved"][1]
    assert base.per_type["CNIC"].recall == 0.0
    assert imp.per_type["CNIC"].recall > base.per_type["CNIC"].recall
    assert imp.per_type["CUSTOMER_ID"].recall > base.per_type["CUSTOMER_ID"].recall
    assert imp.per_type["PHONE_NUMBER"].recall >= base.per_type["PHONE_NUMBER"].recall


def test_improved_leaves_fewer_residuals(runs):
    _r, _g, _t, out = runs
    assert len(out["improved"][0].residuals) < len(out["baseline"][0].residuals)


def test_reports_written_with_expected_columns(runs, tmp_path):
    _r, gt, _t, out = runs
    reports = {m: rep for m, (_res, rep) in out.items()}
    residuals = {m: res.residuals for m, (res, _rep) in out.items()}
    metas = {m: res.engine_meta for m, (res, _rep) in out.items()}
    paths = write_all_metrics(reports, residuals, metas, gt, {}, out_dir=tmp_path)
    for key in ("baseline_metrics", "improved_metrics", "comparison", "per_document", "residual"):
        assert paths[key].exists()
    with open(paths["improved_metrics"], encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert {"entity_type", "gt_count", "tp", "fn", "fp", "recall", "precision", "f1"} <= set(rows[0])
    assert rows[-1]["entity_type"] == "OVERALL"
    with open(paths["comparison"], encoding="utf-8") as f:
        comp = list(csv.DictReader(f))
    assert {"baseline_recall", "improved_recall", "delta_recall"} <= set(comp[0])
    p1 = plot_recall_by_entity(reports["baseline"], reports["improved"], tmp_path / "r.png")
    p2 = plot_precision_recall_comparison(reports["baseline"], reports["improved"], tmp_path / "pr.png")
    assert p1.stat().st_size > 0 and p2.stat().st_size > 0
