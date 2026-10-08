"""
Redaction (Presidio AnonymizerEngine) and residual verification.
Brief test areas: 12 redaction correctness, 13 no-detection documents,
14 multi-entity, 15 overlapping detections, 16 residual verification; plus
repeated occurrences, Unicode, punctuation/whitespace and idempotency.
"""
import pytest

from pii_pipeline.analyzer import analyze_text
from pii_pipeline.evaluation import Prediction
from pii_pipeline.redactor import find_residuals, redact_text
from pii_pipeline.synthetic_data import PlantedEntity


def _gt(text, value, etype, occurrence=0, rid="T-1"):
    start = -1
    for _ in range(occurrence + 1):
        start = text.index(value, start + 1)
    return PlantedEntity(f"{rid}-E{occurrence}", rid, "test", etype, value, start, start + len(value))


def _redact(engine, text):
    return redact_text(text, analyze_text(engine, text, "improved")).text


# 12. single-entity correctness ----------------------------------------------

def test_single_phone_replaced_exactly():
    text = "Call 0321-1234567 now."
    out = redact_text(text, [Prediction(5, 17, "PHONE_NUMBER", 0.9)])
    assert out.text == "Call [PHONE] now." and out.n_replaced == 1


@pytest.mark.parametrize("label,placeholder", [
    ("PERSON", "[PERSON]"), ("PHONE_NUMBER", "[PHONE]"), ("CNIC", "[CNIC]"),
    ("EMAIL_ADDRESS", "[EMAIL]"), ("ADDRESS", "[ADDRESS]"), ("POSTAL_CODE", "[POSTAL_CODE]"),
    ("CUSTOMER_ID", "[CUSTOMER_ID]"),
])
def test_operator_per_label(label, placeholder):
    assert redact_text("xx VALUE yy", [Prediction(3, 8, label, 0.9)]).text == f"xx {placeholder} yy"


def test_unknown_label_uses_fallback():
    assert redact_text("xx VALUE yy", [Prediction(3, 8, "SOMETHING", 0.9)]).text == "xx [REDACTED] yy"


def test_custom_phone_and_cnic_redacted_by_engine(improved_engine):
    out = _redact(improved_engine, "Mobile: +92 300 7654321, CNIC 42101-7654321-5.")
    assert "[PHONE]" in out and "[CNIC]" in out
    assert "7654321" not in out


# 13. no-detection documents --------------------------------------------------

def test_no_predictions_returns_text_unchanged():
    text = "Shift report: 24 x 19L dispatched."
    assert redact_text(text, []).text == text


def test_trap_only_document_unchanged_by_improved(improved_engine):
    text = "Quantity: 12 x 19L. Total PKR 4,500. Invoice 54321 paid on 2026-10-01."
    assert _redact(improved_engine, text) == text


# 14. multiple entities -------------------------------------------------------

def test_multi_entity_document(improved_engine):
    text = ("Customer Name: Ayesha Khan\nEmail: ayesha.khan12@example.org\n"
            "Mobile: 0321-1234567\nAccount ID: UBW-12345\n"
            "Address: House #12, Street 4, Block B, Gulberg III, Lahore 54000")
    out = _redact(improved_engine, text)
    for ph in ("[PERSON]", "[EMAIL]", "[PHONE]", "[CUSTOMER_ID]", "[ADDRESS]", "[POSTAL_CODE]"):
        assert ph in out, ph
    for value in ("Ayesha Khan", "ayesha.khan12@example.org", "0321-1234567", "UBW-12345", "54000"):
        assert value not in out
    assert out.count("\n") == text.count("\n")


# 15. overlapping detections --------------------------------------------------

def test_overlapping_different_labels_leave_no_original_characters():
    text = "ID 4210112345671 end"
    preds = [Prediction(3, 16, "CNIC", 0.65), Prediction(3, 14, "PHONE_NUMBER", 0.4)]
    out = redact_text(text, preds).text
    assert not any(ch.isdigit() for ch in out), out
    assert out.startswith("ID ") and out.endswith(" end")


def test_partially_overlapping_spans_fully_covered():
    text = "Ref ABCDEFGHIJ end"
    preds = [Prediction(4, 10, "PERSON", 0.85), Prediction(7, 14, "ADDRESS", 0.6)]
    out = redact_text(text, preds).text
    # The lower-scored ADDRESS span is trimmed to the part not covered by PERSON,
    # so every original character is replaced.
    assert out == "Ref [PERSON][ADDRESS] end"


def test_nested_same_label_gives_single_placeholder():
    from pii_pipeline.analyzer import normalise_predictions

    class R:  # minimal stand-in for a Presidio RecognizerResult
        def __init__(self, s, e, t, sc):
            self.start, self.end, self.entity_type, self.score = s, e, t, sc
            self.recognition_metadata = {"recognizer_name": "x"}
    text = "Name: Ayesha Khan."
    preds = normalise_predictions([R(6, 17, "PERSON", 0.6), R(13, 17, "PERSON", 0.85)], text)
    assert len(preds) == 1
    assert redact_text(text, preds).text == "Name: [PERSON]."


def test_location_mapped_to_address_placeholder():
    from pii_pipeline.analyzer import normalise_predictions

    class R:
        def __init__(self):
            self.start, self.end, self.entity_type, self.score = 5, 11, "LOCATION", 0.85
            self.recognition_metadata = {"recognizer_name": "SpacyRecognizer"}
    preds = normalise_predictions([R()], "From Lahore today")
    assert preds[0].label == "ADDRESS"
    assert redact_text("From Lahore today", preds).text == "From [ADDRESS] today"


# repeated occurrences, Unicode, punctuation ---------------------------------

def test_repeated_occurrences_all_replaced(improved_engine):
    text = "Primary 03001234567. If busy, try 03001234567 again."
    out = _redact(improved_engine, text)
    assert out.count("[PHONE]") == 2 and "03001234567" not in out


def _only(engine, text, labels):
    return [p for p in analyze_text(engine, text, "improved") if p.label in labels]


def test_unicode_urdu_text_preserved(improved_engine):
    text = "براہ کرم 0330-2554669 پر کال کریں۔ شکریہ"
    out = redact_text(text, _only(improved_engine, text, {"PHONE_NUMBER"})).text
    assert out == "براہ کرم [PHONE] پر کال کریں۔ شکریہ"


def test_urdu_text_full_engine_redacts_phone(improved_engine):
    """With all labels, the phone is replaced and the Urdu prefix is intact.
    (spaCy en_core_web_sm also tags some Urdu tokens as PERSON — a documented
    false-positive source, see docs/LIMITATIONS.md.)"""
    out = _redact(improved_engine, "براہ کرم 0330-2554669 پر کال کریں۔ شکریہ")
    assert out.startswith("براہ کرم [PHONE] ") and "2554669" not in out


def test_accented_text_preserved():
    text = "Café order for Zoë Ahmed, ok."
    s = text.index("Zoë Ahmed")
    out = redact_text(text, [Prediction(s, s + 9, "PERSON", 0.85)]).text
    assert out == "Café order for [PERSON], ok."


def test_punctuation_and_whitespace_preserved(improved_engine):
    text = "Email:\t<a.b12@example.net>;  phone=(0321) 1234567!\n"
    out = redact_text(text, _only(improved_engine, text, {"EMAIL_ADDRESS", "PHONE_NUMBER"})).text
    assert out == "Email:\t<[EMAIL]>;  phone=[PHONE]!\n"


def test_redacting_redacted_text_is_idempotent(improved_engine):
    text = "Customer Name: Ayesha Khan, Mobile: 0321-1234567, CNIC 42101-1234567-1"
    once = _redact(improved_engine, text)
    twice = _redact(improved_engine, once)
    assert twice == once


# 16. residual verification ---------------------------------------------------

def test_residual_found_when_value_survives():
    text = "Call 0321-1234567 now"
    res = find_residuals(text, [_gt(text, "0321-1234567", "PHONE_NUMBER")])
    assert len(res) == 1 and res[0].match_kind == "exact"
    assert "1234567" not in res[0].masked_value


def test_residual_none_after_redaction():
    text = "Call 0321-1234567 now"
    g = _gt(text, "0321-1234567", "PHONE_NUMBER")
    red = redact_text(text, [Prediction(g.start, g.end, "PHONE_NUMBER", 0.9)]).text
    assert find_residuals(red, [g]) == []


def test_residual_digits_with_other_separators():
    g = _gt("x 0321-1234567", "0321-1234567", "PHONE_NUMBER")
    assert find_residuals("number is 03211234567", [g])[0].match_kind == "digits"
    g2 = _gt("x +92 321 1234567", "+92 321 1234567", "PHONE_NUMBER")
    assert find_residuals("call 0321-1234567", [g2])[0].match_kind == "digits"
    g3 = _gt("x 42101-1234567-1", "42101-1234567-1", "CNIC")
    assert find_residuals("id 4210112345671", [g3])[0].match_kind == "digits"


def test_residual_email_case_insensitive():
    g = _gt("x ali.khan@example.org", "ali.khan@example.org", "EMAIL_ADDRESS")
    assert len(find_residuals("mail ALI.KHAN@EXAMPLE.ORG", [g])) == 1


def test_residual_respects_boundaries():
    g = _gt("Postal 12345", "12345", "POSTAL_CODE")
    assert find_residuals("Account UBW-123456 and 512345", [g]) == []
    g2 = _gt("x 0321-1234567", "0321-1234567", "PHONE_NUMBER")
    assert find_residuals("serial 9903211234567", [g2]) == []


def test_partial_redaction_reported_as_residual_free_only_if_value_gone():
    text = "Name: Ayesha Khan"
    g = _gt(text, "Ayesha Khan", "PERSON")
    red = redact_text(text, [Prediction(6, 12, "PERSON", 0.85)]).text   # only "Ayesha"
    assert red == "Name: [PERSON] Khan"
    # The full value no longer appears, so the strict residual check passes;
    # the surname leak is captured by exact-span recall / redaction coverage instead.
    assert find_residuals(red, [g]) == []
