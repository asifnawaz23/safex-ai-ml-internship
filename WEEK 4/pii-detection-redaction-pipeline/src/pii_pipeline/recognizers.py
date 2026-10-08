"""
recognizers.py
--------------
Custom Presidio recognisers added in the improved pipeline (Experiment B).

Why each exists (verified against presidio-analyzer 2.2.364's predefined
English recognisers, see docs/ARCHITECTURE.md):

| Recogniser                     | Entity        | Why                                                   |
|--------------------------------|---------------|-------------------------------------------------------|
| PakistaniPhoneRecognizer       | PHONE_NUMBER  | Built-in PhoneRecognizer has no PK region and a fixed  |
|                                |               | 0.4 score; local formats need explicit boundaries     |
| PakistaniCNICRecognizer        | CNIC          | No default CNIC recogniser exists                      |
| UBWCustomerIDRecognizer        | CUSTOMER_ID   | Company-specific identifier                           |
| PakistaniPostalCodeRecognizer  | POSTAL_CODE   | No default PK postal recogniser exists                |
| PakistaniAddressRecognizer     | ADDRESS       | spaCy only emits LOCATION (often a single city token)  |
| LabelledPersonRecognizer       | PERSON        | spaCy en_core_web_sm misses many South-Asian names in  |
|                                |               | labelled form fields                                  |

Patterns are compiled by Presidio with the third-party ``regex`` module and the
default flags IGNORECASE | MULTILINE | DOTALL. Where case matters (person names),
the pattern uses an inline ``(?-i:...)`` group so it is case-sensitive no matter
which flags Presidio applies.

These recognisers detect *format candidates*. They do not and cannot check
whether a phone number or CNIC is real, assigned, or owned by anyone.
"""

import regex as re
from presidio_analyzer import Pattern, PatternRecognizer

# Gazetteer of major Pakistani cities used as the right anchor of addresses and
# the left anchor of city-suffixed postal codes. Kept independent of the
# generator's vocabulary (it is a superset, not an import).
PK_CITIES = [
    "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan",
    "Peshawar", "Quetta", "Hyderabad", "Sialkot", "Gujranwala", "Bahawalpur",
    "Sargodha", "Sukkur", "Larkana", "Abbottabad", "Mardan", "Gujrat",
    "Sahiwal", "Okara", "Jhelum", "Sheikhupura", "Rahim Yar Khan",
    "Dera Ghazi Khan", "Mirpur", "Muzaffarabad", "Gilgit", "Gwadar",
]

_CITY_ALT = "|".join(sorted(PK_CITIES, key=len, reverse=True))

# Left boundary shared by numeric patterns: not preceded by a word character,
# '+', '-', '.' or '/', so we never start inside a longer code or number.
_LB = r"(?<![\w+\-./])"
# Right boundary: not followed by a word character, '-', or '.<digit>'.
_RB = r"(?![\w\-]|\.\d)"


# ---------------------------------------------------------------------------
# 1. Pakistani mobile phone numbers
# ---------------------------------------------------------------------------
# Supported formats (mobile series 30X-34X):
#   03XX-XXXXXXX   03XX XXXXXXX   03XXXXXXXXX
#   +92 3XX XXXXXXX   +92-3XX-XXXXXXX   +923XXXXXXXXX   +92 3XX XXX XXXX
#   0092-3XX-XXXXXXX  0092 3XX XXXXXXX
#   (03XX) XXXXXXX
#   03XX.XXXXXXX   03XX XXX XXXX            (added after the first evaluation)
# Separators are limited to ONE space, hyphen (or, locally, dot) between groups.

PK_PHONE_PATTERNS = [
    # '.' separator and the 4-3-4 grouping were added after dangerous-miss
    # review DM (phone_dot_separated, phone_local_4_3_4); see CHANGELOG.
    Pattern("pk_phone_local_separated", _LB + r"03[0-4]\d[ \-.]\d{7}" + _RB, 0.85),
    Pattern("pk_phone_local_4_3_4", _LB + r"03[0-4]\d[ \-.]\d{3}[ \-.]\d{4}" + _RB, 0.80),
    Pattern("pk_phone_local_plain", _LB + r"03[0-4]\d{8}" + _RB, 0.70),
    Pattern("pk_phone_intl", _LB + r"(?:\+92|0092)[ \-]?3[0-4]\d[ \-]?\d{7}" + _RB, 0.90),
    Pattern("pk_phone_intl_split", _LB + r"(?:\+92|0092)[ \-]?3[0-4]\d[ \-]\d{3}[ \-]\d{4}" + _RB, 0.90),
    Pattern("pk_phone_parenthesised", r"(?<![\w+\-./])\(03[0-4]\d\)[ ]?\d{7}" + _RB, 0.80),
]

PK_PHONE_CONTEXT = ["phone", "mobile", "contact", "call", "cell", "tel",
                    "whatsapp", "mob", "number", "reach"]


def build_pk_phone_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        name="PakistaniPhoneRecognizer",
        patterns=PK_PHONE_PATTERNS,
        context=PK_PHONE_CONTEXT,
        supported_language="en",
    )


# ---------------------------------------------------------------------------
# 2. Pakistani CNIC-style identity numbers
# ---------------------------------------------------------------------------
# XXXXX-XXXXXXX-X scores 0.90 on its own (the hyphen layout is distinctive).
# 13 contiguous digits score 0.30, BELOW the 0.35 threshold: they are only
# reported when a context word (cnic, nic, nadra, identity, national, card)
# appears in the 5 words before the number (Presidio's LemmaContextAwareEnhancer
# adds 0.35 -> 0.65). This trades recall on unlabelled plain CNICs for
# precision on 13-digit barcodes.

#
# Added after the first evaluation (dangerous-miss review):
#   - XXXXX XXXXXXX X (space-separated 5-7-1 groups), score 0.80.
#   - A label-anchored plain pattern ("NIC:4210112345671"): when the label is
#     glued to the number, spaCy makes "NIC:4210112345671" ONE token, so the
#     context enhancer never sees "NIC" as a preceding word. The label is in a
#     lookbehind and is not part of the span.

_CNIC_LABEL = (r"(?<=\b(?:c?nic|national\s+id(?:entity\s+card)?|nadra\s+id|"
               r"identity\s+(?:no|number|card(?:\s+number)?))\.?\s*(?:no\.?|#)?\s*[:#\-]?\s*)")


class PakistaniCNICRecognizer(PatternRecognizer):
    PATTERNS = [
        Pattern("cnic_hyphenated", r"(?<![\w\-])\d{5}-\d{7}-\d(?![\w\-])", 0.90),
        Pattern("cnic_spaced", r"(?<![\w\-])\d{5} \d{7} \d(?![\w\-])", 0.80),
        Pattern("cnic_plain_labelled", _CNIC_LABEL + r"\d{13}(?![\w\-])", 0.70),
        Pattern("cnic_plain_13", r"(?<![\w\-])\d{13}(?![\w\-])", 0.30),
    ]
    CONTEXT = ["cnic", "nic", "nadra", "identity", "national", "card"]

    def __init__(self):
        super().__init__(
            supported_entity="CNIC",
            name="PakistaniCNICRecognizer",
            patterns=self.PATTERNS,
            context=self.CONTEXT,
            supported_language="en",
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        """Reject placeholder-like values such as 0000000000000."""
        digits = re.sub(r"\D", "", pattern_text)
        return len(set(digits)) <= 1


def build_cnic_recognizer() -> PatternRecognizer:
    return PakistaniCNICRecognizer()


# ---------------------------------------------------------------------------
# 3. Urban Bottled Water customer / account IDs: UBW-DDDDD
# ---------------------------------------------------------------------------

def build_customer_id_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="CUSTOMER_ID",
        name="UBWCustomerIDRecognizer",
        patterns=[Pattern("ubw_customer_id", r"(?<![\w\-])UBW-\d{5}(?![\w\-])", 0.95)],
        context=["account", "customer", "acct", "subscriber"],
        supported_language="en",
    )


# ---------------------------------------------------------------------------
# 4. Pakistani postal codes (5 digits) — labelled or directly after a city
# ---------------------------------------------------------------------------
# A bare \d{5} pattern was rejected: in a probe it fired on invoice numbers,
# on the digits of UBW-12345 and on the first block of CNICs. Both patterns
# below require evidence in front of the number (variable-length lookbehind,
# supported by the `regex` module Presidio uses).

POSTAL_PATTERNS = [
    Pattern("pk_postal_labelled",
            r"(?<=\b(?:postal\s*code|post\s*code|postcode|zip\s*code|zip)\s*(?:no\.?|#)?\s*[:#\-]?\s*)"
            r"\d{5}(?![\w\-])", 0.85),
    Pattern("pk_postal_after_city",
            r"(?<=\b(?:" + _CITY_ALT + r")(?:[ ]?[\-,][ ]?|[ ]))\d{5}(?![\w\-])", 0.60),
]


def build_postal_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="POSTAL_CODE",
        name="PakistaniPostalCodeRecognizer",
        patterns=POSTAL_PATTERNS,
        context=["postal", "postcode", "zip"],
        supported_language="en",
    )


# ---------------------------------------------------------------------------
# 5. Pakistani street / delivery addresses
# ---------------------------------------------------------------------------
# Anchored on a dwelling keyword + number (House #12, House No. 5, H. No. 7,
# Flat 3B, Plot 9, Shop 4, Apartment 2), followed by up to four comma-separated
# segments, and ending at a known city name. Landmark-style descriptions
# ("near X, behind Y market, Lahore") are deliberately NOT targeted; they are
# a held-out format used to measure generalisation honestly.

_ADDRESS_HEAD = (r"\b(?:House\s*(?:No\.?|#)?|H\.?\s*No\.?|Flat|Plot|Shop|Apartment|Apt\.?)"
                 r"\s*#?\s*\d{1,4}[A-Z]?")
_ADDRESS_REGEX = (_ADDRESS_HEAD + r"(?:,[ ]*[^,\n|;<>()]{1,40}?){0,4}?,[ ]*(?:"
                  + _CITY_ALT + r")\b")


def build_address_recognizer() -> PatternRecognizer:
    return PatternRecognizer(
        supported_entity="ADDRESS",
        name="PakistaniAddressRecognizer",
        patterns=[Pattern("pk_dwelling_address", _ADDRESS_REGEX, 0.70)],
        context=["address", "deliver", "drop", "house", "flat"],
        supported_language="en",
    )


# ---------------------------------------------------------------------------
# 6. Labelled person names
# ---------------------------------------------------------------------------
# A capitalised 2-3 token name directly after a common form label followed by
# ':', '=' or '-' (Name:, Customer Name:, Driver:, Recipient:, Subscriber:,
# Handled by:, From:, Customer:) or after a title (Mr, Mrs, Ms). The label is
# in a lookbehind, so it is NOT part of the span. The name part is
# case-sensitive via (?-i:...). Lower-case and ALL-CAPS names are not matched.

_PERSON_LABELS = (r"(?:customer\s+name|full\s+name|name|driver|recipient|subscriber|"
                  r"handled\s+by|from|customer|rider|agent)\s*[:=\-]\s*")
_PERSON_TITLES = r"\b(?:mr|mrs|ms)\.?\s*"
_NAME_TOKEN = r"\p{Lu}\p{Ll}+"
_PERSON_REGEX = (r"(?<=(?:\b" + _PERSON_LABELS + r"|" + _PERSON_TITLES + r"))"
                 r"(?-i:" + _NAME_TOKEN + r"(?:[ ]" + _NAME_TOKEN + r"){1,2})(?![\w])")


class LabelledPersonRecognizer(PatternRecognizer):
    STOP_TOKENS = {"Urban", "Bottled", "Water", "Support", "Team", "Service",
                   "Account", "Customer", "Order", "Delivery", "Subject"}

    def __init__(self):
        super().__init__(
            supported_entity="PERSON",
            name="LabelledPersonRecognizer",
            patterns=[Pattern("labelled_person_name", _PERSON_REGEX, 0.60)],
            context=[],
            supported_language="en",
        )

    def invalidate_result(self, pattern_text: str) -> bool:
        return any(tok in self.STOP_TOKENS for tok in pattern_text.split())


def build_labelled_person_recognizer() -> PatternRecognizer:
    return LabelledPersonRecognizer()


# ---------------------------------------------------------------------------
# 7. Company code allow-list (improved pipeline only)
# ---------------------------------------------------------------------------
# Internal Urban Bottled Water codes with a fixed, documented format that are
# not personal data. In the first evaluation, spaCy tagged "Batch BATCH-4374-B"
# and "van LEB-8555" as PERSON and Presidio's PhoneRecognizer reported the
# digits of "ORD-2026-473869" as a phone number. The improved pipeline drops a
# detection whose span overlaps one of these codes and contains no characters
# outside "<optional keyword> <code>". Unknown code formats are NOT covered.

NON_PII_CODE_REGEX = re.compile(
    r"(?:\b(?:order(?:\s+ref)?|batch|van|vehicle|ref(?:erence)?)\b\s*[:#\-]?\s*)?"
    r"\b(?:ORD-\d{4}-\d{6}|BATCH-\d{4}-[A-Z]|[A-Z]{3}-\d{4})\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------

CUSTOM_RECOGNIZER_NAMES = frozenset({
    "PakistaniPhoneRecognizer", "PakistaniCNICRecognizer", "UBWCustomerIDRecognizer",
    "PakistaniPostalCodeRecognizer", "PakistaniAddressRecognizer", "LabelledPersonRecognizer",
})


def get_all_custom_recognizers() -> list:
    """All custom recognisers used by the improved pipeline (unique names)."""
    return [
        build_pk_phone_recognizer(),
        build_cnic_recognizer(),
        build_customer_id_recognizer(),
        build_postal_recognizer(),
        build_address_recognizer(),
        build_labelled_person_recognizer(),
    ]
