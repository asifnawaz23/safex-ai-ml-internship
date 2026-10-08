"""
Synthetic dataset and ground truth.
Brief test areas: 1 count + uniqueness, 2 GT span integrity, 3 category
coverage, 19 deterministic generation.
"""
import json
from collections import Counter

import pytest

from pii_pipeline import pipeline
from pii_pipeline.ground_truth import (
    load_ground_truth, load_traps, save_ground_truth, save_traps, validate_annotations,
)
from pii_pipeline.synthetic_data import (
    DOC_TYPES, EMAIL_DOMAINS, ENTITY_TYPES, PlantedEntity, generate_dataset, generate_dataset_full,
)


# 1. count + uniqueness -------------------------------------------------------

def test_at_least_800_records(full_dataset):
    records, _, _ = full_dataset
    assert len(records) >= 800


def test_count_is_configurable():
    records, _, _ = generate_dataset_full(seed=42, count=30)
    assert sum(r.source == "planted" for r in records) == 30


def test_record_ids_and_texts_unique(full_dataset):
    records, _, _ = full_dataset
    assert len({r.record_id for r in records}) == len(records)
    assert len({r.text for r in records}) == len(records)


def test_all_records_marked_synthetic(full_dataset):
    records, _, _ = full_dataset
    assert all(r.synthetic for r in records)


# 2. ground-truth span integrity ---------------------------------------------

def test_every_span_matches_text(full_dataset):
    records, gt, traps = full_dataset
    texts = {r.record_id: r.text for r in records}
    for g in gt:
        assert 0 <= g.start < g.end <= len(texts[g.record_id])
        assert texts[g.record_id][g.start:g.end] == g.text, g.annotation_id
    for t in traps:
        assert texts[t.record_id][t.start:t.end] == t.text, t.trap_id


def test_validate_annotations_passes_and_counts(full_dataset):
    records, gt, traps = full_dataset
    summary = validate_annotations(records, gt, traps)
    assert summary["annotations"] == len(gt) and summary["all_offsets_valid"]


def test_validate_annotations_detects_bad_offset(full_dataset):
    records, gt, traps = full_dataset
    g = gt[0]
    bad = PlantedEntity(g.annotation_id, g.record_id, g.doc_type, g.entity_type, g.text,
                        g.start + 1, g.end + 1)
    with pytest.raises(ValueError, match="offset mismatch"):
        validate_annotations(records, [bad] + gt[1:], traps)


def test_traps_never_overlap_ground_truth(full_dataset):
    records, gt, traps = full_dataset
    by_rec = {}
    for g in gt:
        by_rec.setdefault(g.record_id, []).append(g)
    for t in traps:
        for g in by_rec.get(t.record_id, []):
            assert not (t.start < g.end and g.start < t.end)


def test_offsets_are_end_exclusive():
    records, gt, _ = generate_dataset_full(seed=3, count=12)
    texts = {r.record_id: r.text for r in records}
    g = gt[0]
    assert len(texts[g.record_id][g.start:g.end]) == g.end - g.start == len(g.text)


def test_nested_ground_truth_present(full_dataset):
    _, gt, _ = full_dataset
    nested = [g for g in gt if "nested" in g.tags]
    types = {g.entity_type for g in nested}
    assert types == {"ADDRESS", "POSTAL_CODE"}
    addr = next(g for g in nested if g.entity_type == "ADDRESS")
    post = next(g for g in nested if g.entity_type == "POSTAL_CODE")
    assert addr.start <= post.start and post.end <= addr.end


def test_repeated_values_annotated_separately(full_dataset):
    _, gt, _ = full_dataset
    rep = [g for g in gt if g.record_id == "CHAL-011"]
    assert len(rep) == 2 and rep[0].text == rep[1].text and rep[0].start != rep[1].start


def test_ground_truth_roundtrip(tmp_path, full_dataset):
    _, gt, traps = full_dataset
    save_ground_truth(gt[:50], tmp_path / "gt.json")
    save_traps(traps[:20], tmp_path / "traps.json")
    assert [g.to_dict() for g in load_ground_truth(tmp_path / "gt.json")] == [g.to_dict() for g in gt[:50]]
    assert [t.to_dict() for t in load_traps(tmp_path / "traps.json")] == [t.to_dict() for t in traps[:20]]


# 3. category coverage --------------------------------------------------------

def test_all_seven_entity_types_present(full_dataset):
    _, gt, _ = full_dataset
    counts = Counter(g.entity_type for g in gt)
    assert set(counts) == set(ENTITY_TYPES)
    assert all(n >= 100 for n in counts.values()), counts


def test_all_document_types_present(full_dataset):
    records, _, _ = full_dataset
    assert {r.doc_type for r in records} == set(DOC_TYPES)


def test_no_category_dominates(full_dataset):
    _, gt, _ = full_dataset
    counts = Counter(g.entity_type for g in gt)
    assert max(counts.values()) / len(gt) < 0.60


def test_edge_cases_and_traps_present(full_dataset):
    records, gt, traps = full_dataset
    tags = Counter(t for g in gt for t in g.tags)
    for tag in ("cnic_plain", "cnic_hyphen", "no_context", "lowercase_name", "uppercase_name",
                "heldout_format", "unicode_context", "postal_after_city", "repeated_value"):
        assert tags[tag] > 0, tag
    kinds = {t.kind for t in traps}
    assert {"order_number", "bottle_count", "invoice_total", "date", "batch_code", "barcode",
            "tracking_number", "invoice_number", "vehicle_plate"} <= kinds
    assert any(not r.planted_entities for r in records), "expected some records with no PII"


def test_phone_formats_varied(full_dataset):
    _, gt, _ = full_dataset
    fmts = {t for g in gt if g.entity_type == "PHONE_NUMBER" for t in g.tags if t.startswith("phone_")}
    assert len(fmts) >= 10


def test_emails_only_reserved_domains(full_dataset):
    _, gt, _ = full_dataset
    for g in gt:
        if g.entity_type == "EMAIL_ADDRESS":
            assert g.text.lower().rsplit("@", 1)[1] in EMAIL_DOMAINS


def test_phrasing_is_varied(full_dataset):
    """Not one template: first lines of a document type differ widely."""
    records, _, _ = full_dataset
    for dt in DOC_TYPES:
        starts = {r.text[:12] for r in records if r.doc_type == dt and r.source == "planted"}
        assert len(starts) >= 3, dt


# 19. determinism -------------------------------------------------------------

def test_same_seed_identical():
    a = generate_dataset_full(seed=42, count=40)
    b = generate_dataset_full(seed=42, count=40)
    assert [r.text for r in a[0]] == [r.text for r in b[0]]
    assert [g.to_dict() for g in a[1]] == [g.to_dict() for g in b[1]]
    assert [t.to_dict() for t in a[2]] == [t.to_dict() for t in b[2]]


def test_different_seed_differs():
    a, _ = generate_dataset(seed=42, count=20)
    b, _ = generate_dataset(seed=7, count=20)
    assert [r.text for r in a] != [r.text for r in b]


def test_saved_files_hash_identical(tmp_path):
    m1 = pipeline.generate_and_save(seed=42, count=25, out_dir=tmp_path / "a")
    m2 = pipeline.generate_and_save(seed=42, count=25, out_dir=tmp_path / "b")
    assert {k: v["sha256"] for k, v in m1["files"].items()} == {k: v["sha256"] for k, v in m2["files"].items()}
    manifest = json.loads((tmp_path / "a" / "dataset_manifest.json").read_text(encoding="utf-8"))
    assert manifest["seed"] == 42 and manifest["synthetic_only"] is True
