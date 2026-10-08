"""
dangerous_misses.py
-------------------
Select, describe and re-verify the most dangerous false negatives of the
improved pipeline.

Selection (deterministic)
    Candidates are improved-pipeline GT occurrences that were not matched
    exactly (missed > partial > wrong_label). They are ordered by entity
    severity (CNIC > PHONE_NUMBER > EMAIL_ADDRESS > PERSON > ADDRESS >
    POSTAL_CODE > CUSTOMER_ID), then miss category, then annotation id. To
    cover distinct failure modes, at most MAX_PER_DIAGNOSIS cases share the
    same diagnosis. Up to 15 cases are kept.

Before / after
    ``evaluate --snapshot-initial`` stores the selected cases of the first
    run in output/metrics/initial/dangerous_misses_initial.json. Later runs
    re-check exactly those annotation ids against the CURRENT improved
    predictions. A case is only reported as DETECTED_AFTER_FIX when it is now
    an exact match AND the named regression test exists in
    tests/test_regression.py (the test itself is executed by pytest).

Constructed cases
    Only if fewer than 15 actual misses exist, clearly labelled constructed
    adversarial texts are run through the current improved engine and their
    real outcome is recorded.

Excerpts mask every planted value with privacy.mask_value, even though all
data is synthetic.
"""

from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from pii_pipeline import config
from pii_pipeline.privacy import mask_value

MAX_CASES = 15
MAX_PER_DIAGNOSIS = 2
# Brief: CNIC / phone / email / person > address > postal code / customer id
SEVERITY_GROUP = {"CNIC": 1, "PHONE_NUMBER": 1, "EMAIL_ADDRESS": 1, "PERSON": 1,
                  "ADDRESS": 2, "POSTAL_CODE": 3, "CUSTOMER_ID": 3}
SEVERITY = {"CNIC": 1, "PHONE_NUMBER": 2, "EMAIL_ADDRESS": 3, "PERSON": 4,
            "ADDRESS": 5, "POSTAL_CODE": 6, "CUSTOMER_ID": 7}
CATEGORY_RANK = {"missed": 0, "partial": 1, "wrong_label": 2}

WHY_SENSITIVE = {
    "CNIC": "National identity number: a lifelong unique identifier usable for identity fraud and linkage across systems.",
    "PHONE_NUMBER": "Personal mobile number: direct contact channel, enables harassment, SIM-swap and social-engineering attacks.",
    "EMAIL_ADDRESS": "Personal email: direct contact channel and a common login identifier.",
    "PERSON": "Name of a customer or staff member: direct identifier, especially combined with an address or phone.",
    "ADDRESS": "Home/delivery address: locates the person physically.",
    "POSTAL_CODE": "Postal code: quasi-identifier that narrows location when combined with other fields.",
    "CUSTOMER_ID": "Internal account id: linkage key to the full customer record for anyone with CRM access.",
}

# Diagnosis -> explanation. Root causes were written after inspecting the
# affected records of the first full run (see docs/DANGEROUS_MISSES.md).
# by_design=True marks failure modes deliberately left unfixed (trade-off or
# held-out format); they are never reported as fixed.
_MODEL_LIMIT = ("en_core_web_sm is the only NER signal for unlabelled names; the larger spaCy/"
                "Transformer models were excluded by the 8 GB RAM / disk constraints")

KNOWN_ROOT_CAUSES: Dict[str, dict] = {
    "cnic_plain_missed": {
        "root_cause": "Label glued to the number ('NIC:<13 digits>'). spaCy keeps it as one token, so "
                      "Presidio's context enhancer finds no preceding context word and the plain 13-digit "
                      "pattern stays at 0.30, below the 0.35 threshold.",
        "risk": "Full CNIC left in redacted output.",
        "proposed_fix": "Label-anchored plain CNIC pattern (lookbehind on CNIC/NIC/National ID/NADRA ID/"
                        "Identity No.), score 0.70.",
    },
    "cnic_plain_no_context": {
        "root_cause": "Plain 13-digit number with no context word in the 5 preceding words. Scored 0.30 on "
                      "purpose so that 13-digit barcodes are not redacted as CNICs.",
        "risk": "Unlabelled CNIC survives redaction.",
        "proposed_fix": "Not fixed: lowering the score would turn barcodes into CNIC detections. Mitigation: "
                        "human review of documents with long digit runs; a reviewer-facing flag for "
                        "unlabelled 13-digit numbers is future work.",
        "by_design": True,
    },
    "cnic_space_separated": {
        "root_cause": "Held-out format XXXXX XXXXXXX X: the recogniser only knew hyphenated and contiguous "
                      "CNICs.",
        "risk": "Full CNIC left in redacted output.",
        "proposed_fix": "Add a space-separated 5-7-1 pattern (score 0.80).",
    },
    "phone_dot_separated": {
        "root_cause": "Held-out format 03XX.XXXXXXX: the custom separator class was [ -] only and the "
                      "built-in PhoneRecognizer (no PK region) did not report it in these contexts.",
        "risk": "Mobile number left in redacted output.",
        "proposed_fix": "Allow '.' as the local separator.",
    },
    "phone_local_4_3_4": {
        "root_cause": "Held-out grouping 03XX XXX XXXX: no custom pattern; the built-in recogniser missed it.",
        "risk": "Mobile number left in redacted output.",
        "proposed_fix": "Add a 4-3-4 local pattern (score 0.80).",
    },
    "phone_partial": {
        "root_cause": "Two PHONE_NUMBER detections: the built-in PhoneRecognizer returned '(0321-...' "
                      "including the bracket, the custom recogniser the exact number. The original "
                      "normalisation rule 'larger span wins' kept the built-in span.",
        "risk": "Low for redaction (the number is still covered) but the exact-span metric counts a miss.",
        "proposed_fix": "Same-label containment precedence: custom recogniser span wins over a built-in one.",
    },
    "email_partial": {
        "root_cause": "Presidio's EmailRecognizer regex allows '=' in the local part, so in key=value text "
                      "'email=p.hussain@example.com' is matched as one address.",
        "risk": "Low for redaction (over-redaction of the key) but wrong span; downstream parsers lose the key.",
        "proposed_fix": "Span hygiene: drop a leading 'key=' from EMAIL_ADDRESS spans (both modes).",
    },
    "email_uppercase_partial": {
        "root_cause": "Same as email_partial: 'email=' swallowed in key=value text (the upper case was not "
                      "the cause).",
        "risk": "As email_partial.",
        "proposed_fix": "Span hygiene: drop a leading 'key=' from EMAIL_ADDRESS spans (both modes).",
    },
    "person_lowercase_name_missed": {
        "root_cause": "All-lower-case name in free text. The labelled-person pattern is case-sensitive by "
                      "design and en_core_web_sm does not tag lower-case names.",
        "risk": "Customer name left in redacted output.",
        "proposed_fix": "Not fixed: a name gazetteer would also match ordinary words and would be fitted "
                        "to the generator's name list. Human review required.",
        "by_design": True,
    },
    "person_missed": {
        "root_cause": "Unlabelled name in prose ('Visited <name> today ...') not tagged by en_core_web_sm; "
                      "no label for the pattern recogniser. " + _MODEL_LIMIT + ".",
        "risk": "Customer name left in redacted output.",
        "proposed_fix": "Not fixed in this prototype: needs a stronger NER model or more context patterns.",
        "by_design": True,
    },
    "person_three_token_name_missed": {
        "root_cause": "Three-token staff signature after '- ' at the end of a note; not tagged by "
                      "en_core_web_sm and no label precedes it. " + _MODEL_LIMIT + ".",
        "risk": "Staff name left in redacted output.",
        "proposed_fix": "Not fixed: a signature pattern ('- Name Name') is possible but risks FPs on "
                        "capitalised phrases; stronger NER preferred.",
        "by_design": True,
    },
    "person_uppercase_name_missed": {
        "root_cause": "ALL-CAPS name after a short label ('drv:'); en_core_web_sm does not tag it and the "
                      "labelled-person pattern requires capitalised tokens.",
        "risk": "Driver name left in redacted output.",
        "proposed_fix": "Not fixed: an upper-case variant would match headings such as 'DELIVERY NOTE'. "
                        "Human review required.",
        "by_design": True,
    },
    "person_lowercase_name_partial": {
        "root_cause": "spaCy PERSON span ran across the '|' field delimiter into the next field "
                      "('haris hashmi | ph +92').",
        "risk": "Over-redaction of the neighbouring field; exact-span miss.",
        "proposed_fix": "Span hygiene: end PERSON spans at field delimiters, line breaks and digits.",
    },
    "person_no_whitespace_partial": {
        "root_cause": "spaCy PERSON span continued through '(' into the phone number "
                      "('Raza Ahmed(0321-...').",
        "risk": "Over-redaction and wrong label on the phone digits; exact-span miss.",
        "proposed_fix": "Span hygiene: end PERSON spans at field delimiters, line breaks and digits.",
    },
    "person_partial": {
        "root_cause": "spaCy included the form label in the PERSON span ('Subscriber Mahnoor Bukhari').",
        "risk": "Label word over-redacted; exact-span miss.",
        "proposed_fix": "Span hygiene: strip leading form labels/titles from PERSON spans.",
    },
}

# Diagnosis -> regression test (function name in tests/test_regression.py)
REGRESSION_TESTS: Dict[str, str] = {
    "cnic_plain_missed": "test_dm_cnic_label_glued_to_number",
    "cnic_plain_no_context": "test_dm_cnic_plain_no_context_documented_tradeoff",
    "cnic_space_separated": "test_dm_cnic_space_separated",
    "phone_dot_separated": "test_dm_phone_dot_separated",
    "phone_local_4_3_4": "test_dm_phone_4_3_4",
    "phone_partial": "test_dm_phone_custom_span_precedence",
    "email_partial": "test_dm_email_field_key_prefix_trimmed",
    "email_uppercase_partial": "test_dm_email_field_key_prefix_trimmed",
    "person_lowercase_name_partial": "test_dm_person_span_cut_at_field_delimiter",
    "person_no_whitespace_partial": "test_dm_person_span_cut_at_field_delimiter",
    "person_partial": "test_dm_person_leading_label_trimmed",
    # Not fixed by design: strict-xfail tests that document the current miss
    "person_lowercase_name_missed": "test_dm_person_lowercase_name_expected_miss",
    "person_missed": "test_dm_person_unlabelled_in_prose_expected_miss",
    "person_three_token_name_missed": "test_dm_person_three_token_signature_expected_miss",
    "person_uppercase_name_missed": "test_dm_person_uppercase_name_expected_miss",
}


def _metrics_dir() -> Path:
    return config.get_path("output.metrics_dir")


def _initial_dir() -> Path:
    return _metrics_dir() / "initial"


def _regression_file() -> Path:
    return config.ROOT / "tests" / "test_regression.py"


def regression_test_exists(name: str) -> bool:
    if not name:
        return False
    path = _regression_file()
    return path.exists() and f"def {name}(" in path.read_text(encoding="utf-8")


def diagnose(g, category: str) -> str:
    tags = set(g.tags)
    t = g.entity_type
    if t == "PHONE_NUMBER":
        for fmt in ("dot_separated", "local_4_3_4", "parenthesised"):
            if f"phone_{fmt}" in tags:
                return f"phone_{fmt}"
        return f"phone_{category}"
    if t == "CNIC":
        if "cnic_spaced" in tags:
            return "cnic_space_separated"
        if "cnic_plain" in tags and "no_context" in tags:
            return "cnic_plain_no_context"
        if "cnic_plain" in tags:
            return f"cnic_plain_{category}"
        return f"cnic_{category}"
    if t == "EMAIL_ADDRESS":
        if "uppercase_email" in tags:
            return f"email_uppercase_{category}"
        return f"email_{category}"
    if t == "PERSON":
        for tag in ("lowercase_name", "uppercase_name", "single_token_name", "accented_name",
                    "three_token_name", "no_whitespace"):
            if tag in tags:
                return f"person_{tag}_{category}"
        return f"person_{category}"
    if t == "ADDRESS":
        if "heldout_format" in tags:
            return "address_landmark"
        if "addr_abbrev_lower" in tags:
            return f"address_abbrev_lower_{category}"
        if "nested" in tags:
            return f"address_nested_{category}"
        return f"address_{category}"
    if t == "POSTAL_CODE":
        return f"postal_{category}"
    return f"{t.lower()}_{category}"


def _excerpt(text: str, start: int, end: int, gts, width: int = 35) -> str:
    a, b = max(0, start - width), min(len(text), end + width)
    for g in gts:  # never cut a planted value in half at the window edges
        if g.start < a < g.end:
            a = g.start
        if g.start < b < g.end:
            b = g.end
    merged: List[list] = []
    for s, e in sorted((g.start, g.end) for g in gts if g.start >= a and g.end <= b):
        if merged and s < merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], e)
        else:
            merged.append([s, e])
    pieces, pos = [], a
    for s, e in merged:
        pieces.append(text[pos:s])
        pieces.append(mask_value(text[s:e]))
        pos = e
    pieces.append(text[pos:b])
    out = "".join(pieces).replace("\r", " ").replace("\n", " / ")
    return ("..." if a > 0 else "") + out + ("..." if b < len(text) else "")


def _observed(detail, rec_details, text: str) -> str:
    if detail.category in ("partial", "wrong_label"):
        return (f"{detail.category}: predicted {detail.pred_label} [{detail.pred_start}:{detail.pred_end}] "
                f"'{mask_value(text[detail.pred_start:detail.pred_end])}' by {detail.recognizer or '?'} "
                f"vs GT [{detail.gt_start}:{detail.gt_end}]")
    overl = [d for d in rec_details if d.pred_label and d.pred_start < detail.gt_end and d.pred_end > detail.gt_start]
    if overl:
        o = overl[0]
        return (f"missed: only an overlapping {o.pred_label} prediction by {o.recognizer or '?'} "
                f"[{o.pred_start}:{o.pred_end}] (counted as {o.category})")
    return "missed: no prediction overlaps the span"


def select_cases(records, gt, report) -> List[dict]:
    texts = {r.record_id: r.text for r in records}
    gt_by_id = {g.annotation_id: g for g in gt}
    gt_by_rec: Dict[str, list] = {}
    for g in gt:
        gt_by_rec.setdefault(g.record_id, []).append(g)
    details_by_rec: Dict[str, list] = {}
    for d in report.details:
        details_by_rec.setdefault(d.record_id, []).append(d)

    by_diag: Dict[str, list] = {}
    for d in report.false_negatives():
        g = gt_by_id[d.annotation_id]
        by_diag.setdefault(diagnose(g, d.category), []).append((CATEGORY_RANK.get(d.category, 9), g.annotation_id, d, g))
    for lst in by_diag.values():
        lst.sort(key=lambda c: (c[0], c[1]))

    def _diag_key(item):
        _key, lst = item
        etype = lst[0][3].entity_type
        return (SEVERITY_GROUP.get(etype, 9), SEVERITY.get(etype, 9), lst[0][0], _key)

    ordered = sorted(by_diag.items(), key=_diag_key)
    picks = []
    for rnd in range(MAX_PER_DIAGNOSIS):            # round-robin across diagnoses
        for key, lst in ordered:
            if rnd < len(lst):
                picks.append((SEVERITY_GROUP.get(lst[rnd][3].entity_type, 9), rnd, key, lst[rnd]))
    picks.sort(key=lambda p: (p[0], p[1]))           # severity group first, then round
    chosen = []
    for _grp, _rnd, key, (_cat, _aid, d, g) in picks:
        text = texts[g.record_id]
        chosen.append({
            "record_id": g.record_id, "annotation_id": g.annotation_id, "entity_type": g.entity_type,
            "doc_type": g.doc_type, "tags": list(g.tags), "category_before": d.category, "diagnosis": key,
            "excerpt": _excerpt(text, g.start, g.end, gt_by_rec.get(g.record_id, [])),
            "observed_before": _observed(d, details_by_rec.get(g.record_id, []), text),
        })
        if len(chosen) >= MAX_CASES:
            break
    return chosen


def snapshot_initial(records, gt, reports) -> Dict[str, Path]:
    """Save the 'before fixes' state: metric CSVs and the selected cases."""
    d = _initial_dir()
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    for name in ("baseline_metrics.csv", "improved_metrics.csv", "comparison.csv",
                 "experiment_summary.csv", "summary.json"):
        src = _metrics_dir() / name
        if src.exists():
            dst = d / name.replace(".csv", "_initial.csv").replace(".json", "_initial.json")
            shutil.copyfile(src, dst)
            out[f"initial_{name}"] = dst
    cases = select_cases(records, gt, reports["improved"])
    total_fn = len(reports["improved"].false_negatives())
    path = d / "dangerous_misses_initial.json"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"improved_false_negatives": total_fn, "cases": cases}, f, indent=2, ensure_ascii=False)
    out["initial_dangerous_misses"] = path
    return out


def _load_initial() -> Optional[dict]:
    p = _initial_dir() / "dangerous_misses_initial.json"
    if not p.exists():
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def _constructed_cases(start_index: int, needed: int) -> List[dict]:
    """Constructed adversarial texts, executed through the current improved engine."""
    from pii_pipeline.analyzer import analyze_text, build_analyzer
    specs = [
        ("CNIC", "Ref: 4210 1123 4567 1 provided over the phone.", "4210 1123 4567 1"),
        ("PHONE_NUMBER", "Ring 0300 1234 567 after lunch.", "0300 1234 567"),
        ("PHONE_NUMBER", "WhatsApp: +92 (300) 1234567", "+92 (300) 1234567"),
        ("EMAIL_ADDRESS", "mail: ayesha.khan [at] example.org", "ayesha.khan [at] example.org"),
        ("PERSON", "Customer Name: Muhammad Bin Qasim Raza", "Muhammad Bin Qasim Raza"),
        ("ADDRESS", "Deliver to: street 9, house 44, gulberg, lahore", "street 9, house 44, gulberg, lahore"),
    ]
    engine = build_analyzer("improved")
    out = []
    for i, (etype, text, value) in enumerate(specs[:needed]):
        s = text.index(value)
        preds = analyze_text(engine, text, "improved")
        exact = any(p.start == s and p.end == s + len(value) and p.label == etype for p in preds)
        out.append({
            "case_id": f"CON-{start_index + i:03d}", "constructed": True, "record_id": "", "annotation_id": "",
            "entity_type": etype, "doc_type": "constructed", "tags": ["constructed"],
            "excerpt": text.replace(value, mask_value(value)), "category_before": "n/a",
            "category_after": "exact" if exact else "missed", "diagnosis": "constructed_" + etype.lower(),
            "why_sensitive": WHY_SENSITIVE[etype],
            "observed_before": "n/a (constructed, run once with the current engine)",
            "observed_after": "detected exactly" if exact else "not detected exactly",
            "root_cause": "Constructed adversarial format outside the documented patterns.",
            "risk": "Value survives redaction if such a format occurs in real documents.",
            "proposed_fix": "Add a dedicated pattern only if the format is observed in practice.",
            "regression_test": "", "verification_status": "DETECTED" if exact else "STILL_MISSED",
        })
    return out


def build_dangerous_misses(records, gt, improved_report) -> List[dict]:
    initial = _load_initial()
    texts = {r.record_id: r.text for r in records}
    current_fn = {d.annotation_id: d for d in improved_report.false_negatives()}
    details_by_rec: Dict[str, list] = {}
    for d in improved_report.details:
        details_by_rec.setdefault(d.record_id, []).append(d)
    base_cases = initial["cases"] if initial else select_cases(records, gt, improved_report)

    cases = []
    for i, c in enumerate(base_cases, 1):
        info = KNOWN_ROOT_CAUSES.get(c["diagnosis"], {})
        now = current_fn.get(c["annotation_id"])
        after = "exact" if now is None else now.category
        test = REGRESSION_TESTS.get(c["diagnosis"], "")
        if after == "exact":
            status = "DETECTED_AFTER_FIX" if regression_test_exists(test) else "DETECTED_NO_REGRESSION_TEST"
            if c["category_before"] == "exact":
                status = "DETECTED"
        elif info.get("by_design"):
            status = "NOT_FIXED_BY_DESIGN"
        else:
            status = "STILL_MISSED"
        cases.append({
            "case_id": f"DM-{i:03d}", "constructed": False, **c,
            "category_after": after,
            "observed_after": "exact match" if now is None else
            _observed(now, details_by_rec.get(c["record_id"], []), texts[c["record_id"]]),
            "why_sensitive": WHY_SENSITIVE.get(c["entity_type"], ""),
            "root_cause": info.get("root_cause", "Not yet diagnosed."),
            "risk": info.get("risk", ""),
            "proposed_fix": info.get("proposed_fix", ""),
            "regression_test": f"tests/test_regression.py::{test}" if regression_test_exists(test) else "",
            "verification_status": status,
        })
    if len(cases) < MAX_CASES:
        cases += _constructed_cases(1, MAX_CASES - len(cases))
    return cases


CSV_FIELDS = ["case_id", "constructed", "record_id", "annotation_id", "entity_type", "doc_type",
              "diagnosis", "excerpt", "why_sensitive", "category_before", "observed_before",
              "root_cause", "risk", "proposed_fix", "regression_test", "category_after",
              "observed_after", "verification_status", "tags"]


def save_dangerous_misses(cases: List[dict]) -> Dict[str, Path]:
    md = _metrics_dir()
    md.mkdir(parents=True, exist_ok=True)
    csv_path, json_path = md / "dangerous_misses.csv", md / "dangerous_misses.json"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for c in cases:
            row = dict(c)
            row["tags"] = ";".join(c.get("tags", []))
            w.writerow(row)
    initial = _load_initial()
    with open(json_path, "w", encoding="utf-8", newline="\n") as f:
        json.dump({"initial_improved_false_negatives": initial["improved_false_negatives"] if initial else None,
                   "cases": cases}, f, indent=2, ensure_ascii=False)
    return {"dangerous_misses_csv": csv_path, "dangerous_misses_json": json_path}
