"""
Regression tests for defects found during development and for fixed
dangerous misses (docs/DANGEROUS_MISSES.md), plus strict-xfail tests that
document the misses left unfixed by design. Each test names the defect or
case it protects.
"""
import pytest

from conftest import spans  # noqa: F401  (helper shared via conftest)


# --- Development defects (found while auditing the first prototype) --------

def test_d1_nlp_engine_uses_small_model_and_never_downloads(monkeypatch):
    """D1: AnalyzerEngine without an explicit NLP engine silently loads (and
    downloads) en_core_web_lg. build_nlp_engine must use en_core_web_sm and
    raise instead of downloading when the model is missing."""
    import spacy
    from pii_pipeline import analyzer
    engine = analyzer.build_nlp_engine()
    assert list(engine.nlp) == ["en"]
    assert engine.nlp["en"].meta["name"] == "core_web_sm"

    analyzer.build_nlp_engine.cache_clear()
    monkeypatch.setattr(spacy.util, "is_package", lambda name: False)
    try:
        with pytest.raises(RuntimeError, match="not installed"):
            analyzer.build_nlp_engine()
    finally:
        monkeypatch.undo()
        analyzer.build_nlp_engine.cache_clear()


def test_d2_postal_recognizer_has_no_bare_five_digit_pattern(improved_engine):
    """Postal-code FP: a bare \\d{5} pattern fired on invoice numbers, on the
    digits of UBW-12345 and on CNIC blocks."""
    text = "Invoice 54321 for UBW-12345, CNIC 42101-1234567-1."
    assert "POSTAL_CODE" not in [lab for _v, lab in spans(improved_engine, text)]


def test_d3_ner_label_config_kept(improved_engine):
    """Passing an NLP config without ner_model_configuration kept CARDINAL /
    MONEY etc. Presidio's default label config must be preserved."""
    from pii_pipeline.analyzer import build_nlp_engine
    ner = build_nlp_engine().ner_model_configuration
    assert "CARDINAL" in ner.labels_to_ignore and "MONEY" in ner.labels_to_ignore


def test_d4_offsets_recorded_at_construction_not_searched():
    """The prototype located values with text.find(), i.e. the FIRST
    occurrence. A repeated value must get two distinct, correct spans."""
    from pii_pipeline.synthetic_data import generate_dataset_full
    records, gt, _ = generate_dataset_full(seed=42, count=6)
    rec = next(r for r in records if r.record_id == "CHAL-011")
    phones = [g for g in rec.planted_entities if g.entity_type == "PHONE_NUMBER"]
    assert len(phones) == 2 and phones[0].start != phones[1].start
    assert all(rec.text[g.start:g.end] == g.text for g in phones)


def test_d5_plain_13_digit_barcode_without_context_not_cnic(improved_engine):
    """The prototype scored plain 13-digit runs at 0.6 (above threshold) so
    barcodes became CNICs."""
    assert "CNIC" not in [lab for _v, lab in spans(improved_engine, "Barcode 8964000123456 scanned")]


# --- Dangerous misses from the first full evaluation (output/metrics/initial)
# Texts are synthetic re-creations of the failing patterns (same layout,
# different random values), so the tests do not depend on generated files.

def test_dm_cnic_label_glued_to_number(improved_engine):
    """REC-00546: 'Customer NIC:<13 digits>' — spaCy keeps 'NIC:<digits>' as one
    token, so the context word was invisible and the plain pattern stayed at 0.3."""
    text = "Customer Account - UBW-55120\nCustomer NIC:3520298765431\nAction: Verified"
    assert ("3520298765431", "CNIC") in spans(improved_engine, text)
    assert ("4210112345671", "CNIC") in spans(improved_engine, "CNIC:4210112345671")


@pytest.mark.parametrize("text,value", [
    ("CNIC: 21304 7712345 7 (typed with spaces)", "21304 7712345 7"),
    ("National ID: 17101 7151684 2. Please call back.", "17101 7151684 2"),
])
def test_dm_cnic_space_separated(improved_engine, text, value):
    """CHAL-017 / REC-00044: space-separated CNIC groups had no pattern."""
    assert (value, "CNIC") in spans(improved_engine, text)


def test_dm_cnic_plain_no_context_documented_tradeoff(improved_engine):
    """CHAL-013 / REC-00150 / REC-00230: NOT FIXED BY DESIGN. A plain 13-digit
    number without a context word stays below the threshold, because the same
    rule keeps 13-digit barcodes from being redacted as CNICs. If this test
    starts failing, the trade-off changed: update docs/DANGEROUS_MISSES.md."""
    assert "CNIC" not in [lab for _v, lab in spans(improved_engine, "Customer read out 4110198765493 twice.")]
    assert "CNIC" not in [lab for _v, lab in spans(improved_engine, "Pallet barcode 8964000123456.")]


@pytest.mark.parametrize("value", ["0321.8909268", "0300.1234567"])
def test_dm_phone_dot_separated(improved_engine, value):
    """REC-00145: '03XX.XXXXXXX' was a held-out format with no custom pattern."""
    assert (value, "PHONE_NUMBER") in spans(improved_engine, f"Please call {value} on arrival.")


@pytest.mark.parametrize("value", ["0311 323 3407", "0345-678-9012"])
def test_dm_phone_4_3_4(improved_engine, value):
    """REC-00134: '03XX XXX XXXX' grouping was not covered."""
    assert (value, "PHONE_NUMBER") in spans(improved_engine, f"form; phone={value}; topic=delivery")


def test_dm_phone_custom_span_precedence(improved_engine):
    """CHAL-019: the built-in PhoneRecognizer span '(0321-1234567' contained the
    exact custom span; 'larger span wins' kept the wrong one."""
    found = spans(improved_engine, "Contact:Raza Ahmed(0321-1234567)")
    assert ("0321-1234567", "PHONE_NUMBER") in found
    assert ("(0321-1234567", "PHONE_NUMBER") not in found


@pytest.mark.parametrize("text,value", [
    ("name=Ali Raza; email=p.hussain@example.com; phone=03001234567", "p.hussain@example.com"),
    ("name=Ali Raza; email=TAHIRARAZA@EXAMPLE.COM; topic=billing", "TAHIRARAZA@EXAMPLE.COM"),
])
def test_dm_email_field_key_prefix_trimmed(baseline_engine, improved_engine, text, value):
    """REC-00002 / REC-00086: Presidio's email regex accepts '=' in the local
    part, so 'email=' became part of the address in key=value text."""
    assert (value, "EMAIL_ADDRESS") in spans(improved_engine, text)
    assert (value, "EMAIL_ADDRESS") in spans(baseline_engine, text, "baseline")


def test_dm_person_span_cut_at_field_delimiter():
    """REC-00127 / CHAL-019: spaCy PERSON spans ran across '|' and '(' into the
    next field. Span hygiene ends PERSON spans at delimiters and digits."""
    from pii_pipeline.analyzer import normalise_predictions

    class R:
        def __init__(self, s, e):
            self.start, self.end, self.entity_type, self.score = s, e, "PERSON", 0.85
            self.recognition_metadata = {"recognizer_name": "SpacyRecognizer"}
    t1 = "order pls - name haris hashmi | ph +923001234567"
    p1 = normalise_predictions([R(17, 40)], t1)
    assert [(t1[p.start:p.end]) for p in p1] == ["haris hashmi"]
    t2 = "Contact:Raza Ahmed(0321-1234567)"
    p2 = normalise_predictions([R(8, 32)], t2)
    assert [(t2[p.start:p.end]) for p in p2] == ["Raza Ahmed"]


def test_dm_person_leading_label_trimmed():
    """CHAL-008: spaCy returned 'Subscriber Mahnoor Bukhari' as the PERSON span."""
    from pii_pipeline.analyzer import normalise_predictions

    class R:
        start, end, entity_type, score = 0, 26, "PERSON", 0.85
        recognition_metadata = {"recognizer_name": "SpacyRecognizer"}
    text = "Subscriber Mahnoor Bukhari at Flat 3B"
    assert [text[p.start:p.end] for p in normalise_predictions([R()], text)] == ["Mahnoor Bukhari"]


# --- Dangerous misses NOT fixed by design (DM-009 .. DM-012) ----------------
# Strict xfails: each test asserts the DESIRED behaviour (the name is detected
# exactly) and is expected to fail with en_core_web_sm. If one starts passing
# (XPASS -> failure because strict=True), the behaviour changed and
# docs/DANGEROUS_MISSES.md plus the case status must be updated. The texts are
# the exact synthetic records of the first run, because spaCy's behaviour on
# these forms depends on the particular name (a re-created text with other
# names would not reliably reproduce the miss).

_PERSON_LIMIT = "NOT FIXED BY DESIGN: en_core_web_sm limitation, see docs/DANGEROUS_MISSES.md"


@pytest.mark.xfail(strict=True, reason=_PERSON_LIMIT)
def test_dm_person_lowercase_name_expected_miss(improved_engine):
    """CHAL-015: all-lower-case name in free text, no label."""
    text = "spoke to shahid abbasi about the leaking dispenser, will revisit."
    assert ("shahid abbasi", "PERSON") in spans(improved_engine, text)


@pytest.mark.xfail(strict=True, reason=_PERSON_LIMIT)
def test_dm_person_unlabelled_in_prose_expected_miss(improved_engine):
    """REC-00006: unlabelled name after 'Visited'."""
    text = ("Visited Noreen Iqbal today about account UBW-44973. Customer read out 42101-4418934-9 "
            "for verification. Will call back on 03157294150. - wasim tarar")
    assert ("Noreen Iqbal", "PERSON") in spans(improved_engine, text)


@pytest.mark.xfail(strict=True, reason=_PERSON_LIMIT)
def test_dm_person_three_token_signature_expected_miss(improved_engine):
    """REC-00048: three-token staff signature after '- ' at the end of a note."""
    text = ("Spoke with Zara Baig today about account UBW-50499. NIC on file 17101-1167449-3. "
            "Will call back on 0310 2403361. - Alia Javed Tarar")
    assert ("Alia Javed Tarar", "PERSON") in spans(improved_engine, text)


@pytest.mark.xfail(strict=True, reason=_PERSON_LIMIT)
def test_dm_person_uppercase_name_expected_miss(improved_engine):
    """REC-00028: ALL-CAPS driver name after the short label 'drv:'."""
    text = ("DN-751194 | drv: OMAR ABBASI | to: Usman Iqbal | +92 340 378 6401 | "
            "Shop 57, Saddar Bazaar, Peshawar | 39 x 19L")
    assert ("OMAR ABBASI", "PERSON") in spans(improved_engine, text)


def test_fp_company_codes_not_redacted(improved_engine):
    """FP traps of the first run: 'Batch BATCH-4374-B' / 'van LEB-8555' tagged
    PERSON by spaCy, ORD-2026-473869 digits tagged PHONE_NUMBER by Presidio's
    PhoneRecognizer. The improved pipeline's company-code allow-list drops them."""
    text = "Order ORD-2026-473869 shipped. Batch BATCH-4374-B, van LEB-8555."
    assert spans(improved_engine, text) == []
