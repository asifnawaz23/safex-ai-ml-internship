"""
Evaluation metrics on hand-checkable toy examples (brief test area 17).
"""
import pytest

from pii_pipeline.evaluation import (
    Prediction, evaluate, fmt_metric, format_summary, match_record, per_document_rows,
)
from pii_pipeline.synthetic_data import PlantedEntity, TrapAnnotation


def G(rid, etype, start, end, n=0, tags=()):
    return PlantedEntity(f"{rid}-E{n}", rid, "doc", etype, "x" * (end - start), start, end, tags=tuple(tags))


def P(start, end, label, score=0.9):
    return Prediction(start, end, label, score)


def test_exact_match_is_tp():
    rep = evaluate([G("R1", "PHONE_NUMBER", 0, 12)], {"R1": [P(0, 12, "PHONE_NUMBER")]})
    m = rep.per_type["PHONE_NUMBER"]
    assert (m.tp, m.fn, m.fp) == (1, 0, 0)
    assert m.recall == 1.0 and m.precision == 1.0 and m.f1 == 1.0


def test_miss_and_spurious():
    gt = [G("R1", "CNIC", 0, 15)]
    rep = evaluate(gt, {"R1": [P(20, 25, "POSTAL_CODE")]})
    assert rep.per_type["CNIC"].fn == 1 and rep.per_type["CNIC"].recall == 0.0
    assert rep.per_type["CNIC"].precision is None          # no CNIC predictions
    assert rep.per_type["POSTAL_CODE"].fp == 1
    assert rep.per_type["POSTAL_CODE"].recall is None       # no POSTAL_CODE ground truth
    assert sorted(d.category for d in rep.details) == ["missed", "spurious"]


def test_wrong_label_counts_fn_and_fp():
    rep = evaluate([G("R1", "ADDRESS", 5, 10)], {"R1": [P(5, 10, "PERSON")]})
    assert rep.per_type["ADDRESS"].fn == 1 and rep.per_type["ADDRESS"].wrong_label == 1
    assert rep.per_type["PERSON"].fp == 1
    assert rep.overall.tp == 0


def test_partial_overlap_not_tp_but_overlap_recall():
    rep = evaluate([G("R1", "PERSON", 0, 11)], {"R1": [P(0, 6, "PERSON")]})
    m = rep.per_type["PERSON"]
    assert (m.tp, m.fn, m.fp, m.partial) == (0, 1, 1, 1)
    assert m.recall == 0.0 and m.overlap_recall == 1.0
    assert m.redaction_coverage == 0.0      # characters 6..11 not covered


def test_duplicate_prediction_is_fp():
    rep = evaluate([G("R1", "EMAIL_ADDRESS", 0, 10)],
                   {"R1": [P(0, 10, "EMAIL_ADDRESS"), P(2, 8, "EMAIL_ADDRESS", 0.5)]})
    m = rep.per_type["EMAIL_ADDRESS"]
    assert (m.tp, m.fp, m.duplicate) == (1, 1, 1)
    assert m.precision == 0.5


def test_one_prediction_cannot_match_two_gt():
    gt = [G("R1", "PHONE_NUMBER", 0, 12, 0), G("R1", "PHONE_NUMBER", 0, 12, 1)]
    rep = evaluate(gt, {"R1": [P(0, 12, "PHONE_NUMBER")]})
    assert rep.per_type["PHONE_NUMBER"].tp == 1 and rep.per_type["PHONE_NUMBER"].fn == 1


def test_identical_values_twice_both_need_predictions():
    gt = [G("R1", "PHONE_NUMBER", 0, 11, 0), G("R1", "PHONE_NUMBER", 30, 41, 1)]
    rep = evaluate(gt, {"R1": [P(0, 11, "PHONE_NUMBER"), P(30, 41, "PHONE_NUMBER")]})
    assert rep.per_type["PHONE_NUMBER"].tp == 2 and rep.per_type["PHONE_NUMBER"].recall == 1.0


def test_nested_ground_truth_independent_targets():
    gt = [G("R1", "ADDRESS", 0, 40, 0), G("R1", "POSTAL_CODE", 35, 40, 1)]
    rep = evaluate(gt, {"R1": [P(0, 40, "ADDRESS"), P(35, 40, "POSTAL_CODE")]})
    assert rep.overall.tp == 2 and rep.overall.fp == 0
    rep2 = evaluate(gt, {"R1": [P(0, 40, "ADDRESS")]})
    assert rep2.per_type["POSTAL_CODE"].fn == 1
    assert rep2.per_type["POSTAL_CODE"].redaction_coverage == 1.0   # covered by the address


def test_hand_computed_precision_recall_f1():
    # 4 GT, 3 exact hits, 1 miss, 2 spurious -> R=3/4, P=3/5, F1=2PR/(P+R)=0.6667
    gt = [G("R1", "PERSON", 0, 5, 0), G("R1", "PERSON", 10, 15, 1),
          G("R2", "PERSON", 0, 5, 2), G("R2", "PERSON", 10, 15, 3)]
    preds = {"R1": [P(0, 5, "PERSON"), P(10, 15, "PERSON"), P(20, 25, "PERSON")],
             "R2": [P(0, 5, "PERSON"), P(30, 35, "PERSON")]}
    m = evaluate(gt, preds).per_type["PERSON"]
    assert (m.tp, m.fn, m.fp) == (3, 1, 2)
    assert m.recall == pytest.approx(0.75)
    assert m.precision == pytest.approx(0.6)
    assert m.f1 == pytest.approx(2 * 0.75 * 0.6 / 1.35)


def test_zero_denominators_are_na():
    rep = evaluate([], {"R1": []}, doc_types={"R1": "doc"})
    m = rep.per_type["CNIC"]
    assert m.recall is None and m.precision is None and m.f1 is None
    assert fmt_metric(m.recall) == "N/A"
    assert "N/A" in format_summary(rep)   # OVERALL row: 0 GT and 0 predictions


def test_records_without_gt_still_count_fps():
    rep = evaluate([], {"R9": [P(0, 4, "PERSON")]}, doc_types={"R9": "delivery_note"})
    assert rep.per_type["PERSON"].fp == 1
    assert rep.per_doc_type["delivery_note"].fp == 1


def test_trap_hit_rate():
    traps = [TrapAnnotation("R1-T1", "R1", "doc", "order_number", "x" * 6, 0, 6),
             TrapAnnotation("R1-T2", "R1", "doc", "date", "x" * 10, 20, 30)]
    rep = evaluate([], {"R1": [P(2, 5, "PHONE_NUMBER")]}, traps=traps, doc_types={"R1": "doc"})
    assert (rep.trap_hits, rep.trap_total) == (1, 2) and rep.trap_hit_rate == 0.5
    assert rep.trap_hits_by_kind == {"date": (0, 1), "order_number": (1, 1)}


def test_matching_is_deterministic_under_input_order():
    gt = [G("R1", "PERSON", 0, 10, 0), G("R1", "ADDRESS", 12, 30, 1)]
    preds = [P(12, 30, "ADDRESS"), P(0, 6, "PERSON", 0.5), P(0, 10, "PERSON")]
    a = match_record("R1", gt, preds)
    b = match_record("R1", list(reversed(gt)), list(reversed(preds)))
    assert [(d.category, d.annotation_id, d.pred_start, d.pred_end) for d in a] == \
           [(d.category, d.annotation_id, d.pred_start, d.pred_end) for d in b]


def test_per_doc_type_and_tags():
    gt = [G("R1", "PHONE_NUMBER", 0, 5, 0, tags=("heldout_format",)),
          G("R1", "PHONE_NUMBER", 10, 15, 1)]
    rep = evaluate(gt, {"R1": [P(10, 15, "PHONE_NUMBER")]})
    assert rep.per_tag["heldout_format"].recall == 0.0
    rows = per_document_rows(rep)
    assert rows[0]["tp"] == 1 and rows[0]["fn"] == 1 and rows[0]["all_gt_exact"] is False


def test_partial_leak_counted_next_to_value_residuals():
    """Review finding 4: a partly redacted address is not a whole-value residual
    but must still show up as a partial leak in the residual report."""
    from pii_pipeline.reporting import residual_summary_rows
    gt = [G("R1", "ADDRESS", 0, 30, 0), G("R1", "PERSON", 40, 50, 1), G("R1", "PHONE_NUMBER", 60, 72, 2)]
    preds = {"R1": [P(20, 30, "ADDRESS"), P(60, 72, "PHONE_NUMBER")]}   # address 0..20 survives, person missed
    rep = evaluate(gt, preds)
    assert sorted(rep.uncovered_ids) == ["R1-E0", "R1-E1"]
    residuals = [{"record_id": "R1", "annotation_id": "R1-E1", "entity_type": "PERSON",
                  "masked_value": "x", "match_kind": "exact"}]          # the missed name survives whole
    rows = {r["entity_type"]: r for r in residual_summary_rows("improved", residuals, gt, rep)}
    assert (rows["ADDRESS"]["residual_count"], rows["ADDRESS"]["not_fully_redacted"],
            rows["ADDRESS"]["partial_leaks_not_value_matched"]) == (0, 1, 1)
    assert (rows["PERSON"]["residual_count"], rows["PERSON"]["not_fully_redacted"],
            rows["PERSON"]["partial_leaks_not_value_matched"]) == (1, 1, 0)
    assert (rows["PHONE_NUMBER"]["not_fully_redacted"], rows["OVERALL"]["not_fully_redacted"],
            rows["OVERALL"]["partial_leaks_not_value_matched"]) == (0, 2, 1)