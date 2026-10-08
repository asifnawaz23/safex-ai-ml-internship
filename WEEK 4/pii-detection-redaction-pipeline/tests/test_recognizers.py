"""
Custom and built-in recogniser behaviour.
Brief test areas: 4 PK phone positives, 5 PK phone negatives, 6 CNIC
positives, 7 CNIC negatives, 8 email, 9 person, 10 address + postal,
11 customer ID.

Pattern-level tests call the custom recogniser directly (no context
enhancement); tests that depend on context words go through the improved
AnalyzerEngine.
"""
import pytest

from conftest import spans
from pii_pipeline.recognizers import (
    build_address_recognizer, build_cnic_recognizer, build_customer_id_recognizer,
    build_labelled_person_recognizer, build_pk_phone_recognizer, build_postal_recognizer,
    get_all_custom_recognizers,
)


def _direct(recognizer, text):
    entity = recognizer.supported_entities[0]
    return [(text[r.start:r.end], round(r.score, 2))
            for r in recognizer.analyze(text, [entity]) if r.score >= 0.35]


PHONE = build_pk_phone_recognizer()
CNIC = build_cnic_recognizer()
CUSTID = build_customer_id_recognizer()
POSTAL = build_postal_recognizer()
ADDRESS = build_address_recognizer()
PERSON = build_labelled_person_recognizer()


def test_custom_recognizer_names_unique():
    names = [r.name for r in get_all_custom_recognizers()]
    assert len(names) == len(set(names)) == 6


# 4. Pakistani phone positives ------------------------------------------------

@pytest.mark.parametrize("value", [
    "0321-1234567", "03211234567", "0321 1234567",
    "+92 321 1234567", "+92 321 123 4567", "+923211234567", "+92-321-1234567",
    "0092-321-1234567", "0092 321 1234567", "(0321) 1234567",
])
def test_pk_phone_positive(value):
    text = f"Contact the customer on {value} today."
    assert _direct(PHONE, text) and _direct(PHONE, text)[0][0] == value


@pytest.mark.parametrize("value", ["0300-7654321", "+923451234567", "0092 340 9999999"])
def test_pk_phone_detected_by_improved_engine(improved_engine, value):
    text = f"Mobile: {value}"
    assert (value, "PHONE_NUMBER") in spans(improved_engine, text)


# 5. Pakistani phone negatives (custom recogniser must not match) -------------

@pytest.mark.parametrize("text", [
    "Reference 1234567890 attached",           # 10 digits, no 03 prefix
    "Office line 042-1234567",                 # Lahore landline
    "Landline +92 21 1234567",                 # Karachi landline, not 3XX mobile
    "Run 03211234567890 finished",             # 14-digit run
    "Code ORD-2026-03001234567X",              # digits inside a longer code
    "CNIC 42101-1234567-1",                    # CNIC, not a phone
    "Count 0321-123456",                       # too few digits
    "Count 0321-12345678",                     # too many digits
    "Tracking 72019384756",                    # 11 digits not starting with 03
])
def test_pk_phone_negative(text):
    assert _direct(PHONE, text) == []


def test_builtin_phone_recognizer_flags_plain_10_digits(baseline_engine):
    """Documented baseline characteristic: Presidio's PhoneRecognizer (score 0.4)
    reports '1234567890' as a phone. The custom recogniser does not (above)."""
    assert ("1234567890", "PHONE_NUMBER") in spans(baseline_engine, "Reference 1234567890 attached", "baseline")


# 6. CNIC positives -----------------------------------------------------------

def test_cnic_hyphenated_without_context():
    assert _direct(CNIC, "Value 35202-1234567-3 noted") == [("35202-1234567-3", 0.9)]


@pytest.mark.parametrize("label", ["CNIC:", "NIC #", "National ID", "identity card number", "NADRA ID"])
def test_cnic_plain_with_context(improved_engine, label):
    text = f"{label} 4210112345671 on file."
    assert ("4210112345671", "CNIC") in spans(improved_engine, text)


def test_cnic_hyphenated_in_sentence(improved_engine):
    text = "The customer, whose CNIC is 61101-7654321-9, asked for a refund."
    assert ("61101-7654321-9", "CNIC") in spans(improved_engine, text)


# 7. CNIC negatives -----------------------------------------------------------

def test_cnic_plain_without_context_below_threshold(improved_engine):
    """13-digit barcodes must not become CNICs without a context word."""
    labels = [lab for _v, lab in spans(improved_engine, "Pallet barcode 8964000123456 scanned.")]
    assert "CNIC" not in labels


@pytest.mark.parametrize("text", [
    "Serial 42101123456712 x",      # 14 digits
    "Serial 421011234567 x",        # 12 digits
    "Phone 03211234567",            # 11-digit phone
    "Code 42101-1234567-12",        # extra digit
    "Batch X42101-1234567-1",       # glued to letters
])
def test_cnic_negative_patterns(text):
    assert _direct(CNIC, text) == []


def test_cnic_repeated_digit_invalidated(improved_engine):
    assert "CNIC" not in [lab for _v, lab in spans(improved_engine, "CNIC: 0000000000000")]


# 8. email ---------------------------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("Email: ali.khan12@example.org", "ali.khan12@example.org"),
    ("Write to AYESHA.KHAN@EXAMPLE.NET please", "AYESHA.KHAN@EXAMPLE.NET"),
    ("cc <bilal_q@example.com>.", "bilal_q@example.com"),
    ("contact (s.malik+water@example.org) now", "s.malik+water@example.org"),
])
def test_email_detected(improved_engine, text, value):
    assert (value, "EMAIL_ADDRESS") in spans(improved_engine, text)


def test_email_not_flagged_without_at_sign(improved_engine):
    assert "EMAIL_ADDRESS" not in [lab for _v, lab in spans(improved_engine, "Visit example.org for plans")]


# 9. person --------------------------------------------------------------------

@pytest.mark.parametrize("text,value", [
    ("Customer Name: Ayesha Khan", "Ayesha Khan"),
    ("Recipient: Bilal Qureshi", "Bilal Qureshi"),
    ("Handled by: Saima Mirza Toor", "Saima Mirza Toor"),
    ("Approved by Mr.Qasim Raza today", "Qasim Raza"),
    ("Customer Name: Zoë Ahmed", "Zoë Ahmed"),
])
def test_labelled_person_pattern(text, value):
    assert [v for v, _s in _direct(PERSON, text)] == [value]


def test_labelled_person_is_case_sensitive():
    """Lower-case / ALL-CAPS names are a documented limitation."""
    assert _direct(PERSON, "customer name: ayesha khan") == []
    assert _direct(PERSON, "Customer Name: AYESHA KHAN") == []


def test_labelled_person_excludes_stop_tokens():
    assert _direct(PERSON, "From: Customer Service") == []


def test_person_detected_by_improved_engine(improved_engine):
    assert ("Ayesha Khan", "PERSON") in spans(improved_engine, "Customer Name: Ayesha Khan")


# 10. address + postal ---------------------------------------------------------

@pytest.mark.parametrize("value", [
    "House #12, Street 4, Block B, Gulberg III, Lahore",
    "House No. 45, Canal Road, Model Town, Lahore",
    "H. No. 7, Jail Road, Multan",
    "Flat 3B, Sky Towers, DHA Phase 6, Karachi",
    "Plot 942, Sector F-7/3, Islamabad",
    "Shop 4, Moon Market, Rawalpindi",
    "h no 12, st 4, johar town, lahore",
])
def test_address_pattern(value):
    text = f"Deliver to: {value} 54000 before noon"
    assert [v for v, _s in _direct(ADDRESS, text)] == [value]


def test_landmark_address_not_targeted():
    """Held-out format: documented expected miss for the custom recogniser."""
    assert _direct(ADDRESS, "Drop near Jamia Masjid, behind Liberty Market, Lahore") == []


@pytest.mark.parametrize("text,value", [
    ("Postal Code: 54000", "54000"),
    ("postcode 75500.", "75500"),
    ("ZIP - 44000", "44000"),
    ("Gulberg III, Lahore 54660", "54660"),
    ("Moon Market, Rawalpindi-46000", "46000"),
    ("Clifton, Karachi - 75600", "75600"),
])
def test_postal_positive(text, value):
    assert [v for v, _s in _direct(POSTAL, text)] == [value]


@pytest.mark.parametrize("text", [
    "Invoice #54321 paid", "Account UBW-12345", "CNIC 42101-1234567-1",
    "Total PKR 54,000", "Order 548213", "Lahore 540001",
])
def test_postal_negative(text):
    assert _direct(POSTAL, text) == []


def test_address_and_adjacent_postal_engine(improved_engine):
    text = "Address: House #12, Street 4, Block B, Gulberg III, Lahore 54000"
    found = spans(improved_engine, text)
    assert ("House #12, Street 4, Block B, Gulberg III, Lahore", "ADDRESS") in found
    assert ("54000", "POSTAL_CODE") in found


# 11. customer ID -------------------------------------------------------------

@pytest.mark.parametrize("text,value", [("Account ID: UBW-12345", "UBW-12345"),
                                        ("acct ubw-99881 closed", "ubw-99881"),
                                        ("(UBW-40213)", "UBW-40213")])
def test_customer_id_positive(text, value):
    assert [v for v, _s in _direct(CUSTID, text)] == [value]


@pytest.mark.parametrize("text", ["UBW-123456", "XUBW-12345", "UBW-1234", "UBW-12345-A", "ABC-12345"])
def test_customer_id_negative(text):
    assert _direct(CUSTID, text) == []
