"""
synthetic_data.py
-----------------
Reproducible generator of fictional Urban Bottled Water Company documents with
independent ground truth.

How ground truth stays independent of any detector
    Each document is assembled segment by segment with ``_DocBuilder``. When a
    PII value (or a false-positive trap) is appended, its start offset is the
    current buffer length, so offsets are known by construction. Nothing is
    searched for in the finished text and no detector output is consulted.
    After assembly every span is re-checked with ``text[start:end] == value``.

Offsets are 0-based, end-exclusive (Python slicing convention).

Document types
    delivery_order, contact_form, subscription_record, delivery_note,
    customer_service_message, internal_operational_note

Entity types
    PERSON, PHONE_NUMBER, CNIC, EMAIL_ADDRESS, ADDRESS, POSTAL_CODE, CUSTOMER_ID

Address convention
    An ADDRESS span runs from the dwelling keyword (House/Flat/Plot/...) to the
    city name. A postal code written after the city is a separate, adjacent
    POSTAL_CODE span. One challenge record contains a postal code nested inside
    an ADDRESS span (tag ``nested``) to exercise nested ground truth.

Held-out formats
    A small share of values use formats the custom recognisers were NOT
    written for (tag ``heldout_format``): dot-separated and 4-3-4 spaced
    phones, space-separated CNICs, landmark-style addresses. They measure
    generalisation instead of rewarding recognisers fitted to the generator.

All values are fictional: names come from fixed lists, phone/CNIC digits are
random, and emails use only example.com / example.org / example.net.

Usage
    from pii_pipeline.synthetic_data import generate_dataset_full
    records, ground_truth, traps = generate_dataset_full(seed=42, count=850)
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

GENERATOR_VERSION = "2.0.0"

DOC_TYPES = [
    "delivery_order",
    "contact_form",
    "subscription_record",
    "delivery_note",
    "customer_service_message",
    "internal_operational_note",
]

ENTITY_TYPES = [
    "PERSON", "PHONE_NUMBER", "CNIC", "EMAIL_ADDRESS",
    "ADDRESS", "POSTAL_CODE", "CUSTOMER_ID",
]

EMAIL_DOMAINS = ["example.com", "example.org", "example.net"]
COMPANY_NAME = "Urban Bottled Water Co."


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class PlantedEntity:
    """One ground-truth PII occurrence inside a document."""
    annotation_id: str
    record_id: str
    doc_type: str
    entity_type: str
    text: str                 # exact substring planted in the document
    start: int                # 0-based, inclusive
    end: int                  # 0-based, exclusive
    source: str = "planted"   # planted | challenge
    expected_handling: str = "REDACT"
    tags: Tuple[str, ...] = ()

    def validate(self, document_text: str) -> bool:
        return document_text[self.start:self.end] == self.text

    def to_dict(self) -> dict:
        return {
            "annotation_id": self.annotation_id,
            "record_id": self.record_id,
            "doc_type": self.doc_type,
            "entity_type": self.entity_type,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "source": self.source,
            "expected_handling": self.expected_handling,
            "tags": list(self.tags),
        }


@dataclass
class TrapAnnotation:
    """A non-PII string that looks like PII (false-positive trap)."""
    trap_id: str
    record_id: str
    doc_type: str
    kind: str                 # order_number, invoice_total, date, ...
    text: str
    start: int
    end: int
    expected_handling: str = "KEEP"
    tags: Tuple[str, ...] = ()

    def validate(self, document_text: str) -> bool:
        return document_text[self.start:self.end] == self.text

    def to_dict(self) -> dict:
        return {
            "trap_id": self.trap_id,
            "record_id": self.record_id,
            "doc_type": self.doc_type,
            "kind": self.kind,
            "text": self.text,
            "start": self.start,
            "end": self.end,
            "expected_handling": self.expected_handling,
            "tags": list(self.tags),
        }


@dataclass
class SyntheticRecord:
    """One generated document."""
    record_id: str
    doc_type: str
    text: str
    source: str = "planted"
    synthetic: bool = True
    planted_entities: List[PlantedEntity] = field(default_factory=list)
    traps: List[TrapAnnotation] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "doc_type": self.doc_type,
            "source": self.source,
            "synthetic": self.synthetic,
            "text": self.text,
        }


# ---------------------------------------------------------------------------
# Document builder: offsets recorded at append time
# ---------------------------------------------------------------------------

class _DocBuilder:
    def __init__(self, record_id: str, doc_type: str, source: str = "planted"):
        self.record_id = record_id
        self.doc_type = doc_type
        self.source = source
        self._parts: List[str] = []
        self._len = 0
        self._ents: List[Tuple[str, str, int, int, Tuple[str, ...]]] = []
        self._traps: List[Tuple[str, str, int, int, Tuple[str, ...]]] = []
        self._open: List[Tuple[str, int, Tuple[str, ...]]] = []

    def t(self, s: str) -> "_DocBuilder":
        self._parts.append(s)
        self._len += len(s)
        return self

    def pii(self, value: str, entity_type: str, tags: Sequence[str] = ()) -> "_DocBuilder":
        start = self._len
        self.t(value)
        self._ents.append((entity_type, value, start, self._len, tuple(tags)))
        return self

    def trap(self, value: str, kind: str, tags: Sequence[str] = ()) -> "_DocBuilder":
        start = self._len
        self.t(value)
        self._traps.append((kind, value, start, self._len, tuple(tags)))
        return self

    def open(self, entity_type: str, tags: Sequence[str] = ()) -> "_DocBuilder":
        """Start an entity whose value is assembled from several segments."""
        self._open.append((entity_type, self._len, tuple(tags)))
        return self

    def close(self) -> "_DocBuilder":
        entity_type, start, tags = self._open.pop()
        value = "".join(self._parts)[start:self._len]
        self._ents.append((entity_type, value, start, self._len, tags))
        return self

    @property
    def has_pii(self) -> bool:
        return bool(self._ents)

    def build(self) -> SyntheticRecord:
        if self._open:
            raise RuntimeError(f"{self.record_id}: unclosed entity span")
        text = "".join(self._parts)
        ents = sorted(self._ents, key=lambda e: (e[2], e[3], e[0]))
        planted = [
            PlantedEntity(
                annotation_id=f"{self.record_id}-E{i + 1:02d}",
                record_id=self.record_id,
                doc_type=self.doc_type,
                entity_type=etype,
                text=value,
                start=start,
                end=end,
                source=self.source,
                tags=tags,
            )
            for i, (etype, value, start, end, tags) in enumerate(ents)
        ]
        traps = [
            TrapAnnotation(
                trap_id=f"{self.record_id}-T{i + 1:02d}",
                record_id=self.record_id,
                doc_type=self.doc_type,
                kind=kind,
                text=value,
                start=start,
                end=end,
                tags=tags,
            )
            for i, (kind, value, start, end, tags) in enumerate(
                sorted(self._traps, key=lambda e: (e[2], e[3])))
        ]
        rec = SyntheticRecord(self.record_id, self.doc_type, text, self.source,
                              True, planted, traps)
        for item in list(planted) + list(traps):
            if not item.validate(text):
                raise RuntimeError(f"{self.record_id}: span validation failed")
        return rec


# ---------------------------------------------------------------------------
# Vocabulary (fictional)
# ---------------------------------------------------------------------------

FIRST_NAMES = [
    "Ayesha", "Bilal", "Fatima", "Hassan", "Iqra", "Junaid", "Kiran", "Layla",
    "Nadia", "Omar", "Parveen", "Qasim", "Rabia", "Saad", "Tahira", "Usman",
    "Wasim", "Zara", "Asif", "Bina", "Dania", "Ehsan", "Farhat", "Ghulam",
    "Hira", "Imran", "Jawad", "Kinza", "Luqman", "Mahnoor", "Naveed", "Palwasha",
    "Rizwan", "Saima", "Tariq", "Uzma", "Waqar", "Yusra", "Zahida", "Alia",
    "Burhan", "Faizan", "Sana", "Hamza", "Mehwish", "Shahid", "Noreen", "Adeel",
]

LAST_NAMES = [
    "Ahmed", "Baig", "Chaudhry", "Durrani", "Farooqi", "Ghani", "Hashmi",
    "Iqbal", "Javed", "Khan", "Lodhi", "Mirza", "Niazi", "Pervez", "Qureshi",
    "Raza", "Sheikh", "Toor", "Usmani", "Waheed", "Yaqoob", "Zuberi", "Ansari",
    "Bukhari", "Cheema", "Dogar", "Gillani", "Hussain", "Janjua", "Kayani",
    "Leghari", "Malik", "Osmani", "Rajput", "Siddiqui", "Tarar", "Abbasi",
]

MIDDLE_NAMES = ["Ali", "Ahmed", "Hassan", "Bano", "Noor", "Javed"]

CITIES = [
    "Karachi", "Lahore", "Islamabad", "Rawalpindi", "Faisalabad", "Multan",
    "Peshawar", "Quetta", "Hyderabad", "Sialkot", "Gujranwala", "Bahawalpur",
]

LOCALITIES = [
    "Gulberg III", "Johar Town", "Model Town", "DHA Phase 5", "Bahria Town",
    "Clifton", "North Nazimabad", "Gulshan-e-Iqbal", "Satellite Town", "Cantt",
    "Wapda Town", "Saddar", "Garden Town", "Faisal Town", "Shadman",
]

ROADS = [
    "Main Boulevard", "Canal Road", "Ferozepur Road", "Tariq Road",
    "University Road", "Jail Road", "Mall Road", "Murree Road",
    "Shahrah-e-Faisal", "MM Alam Road", "Allama Iqbal Road",
]

BUILDINGS = ["Al-Noor Heights", "Sky Towers", "Gulshan Residency",
             "Crescent Apartments", "Pearl Residencia", "Askari Tower 2"]

PHASES = ["DHA Phase 6", "Bahria Town Phase 4", "Askari 11", "Clifton Block 5",
          "Gulistan-e-Jauhar Block 15"]

MARKETS = ["Liberty Market", "Jinnah Super Market", "Saddar Bazaar",
           "Anarkali Bazaar", "Hyderi Market", "Moon Market"]

LANDMARKS = ["Jamia Masjid", "the old water tank", "Green Valley school",
             "the PSO petrol pump", "City Hospital gate", "the main roundabout"]

ISLAMABAD_SECTORS = ["G-9/2", "F-7/3", "I-8/4", "G-11/1", "F-10/2", "E-11/3"]

CNIC_PREFIXES = ["42101", "35202", "61101", "38401", "33101",
                 "21304", "17101", "55202", "41302", "52101"]

MOBILE_PREFIXES = ["300", "301", "303", "305", "306", "310", "311", "312",
                   "313", "315", "321", "322", "323", "330", "331", "333",
                   "334", "335", "336", "340", "341", "345"]

PLANS = ["Basic (2 x 19L per week)", "Standard (4 x 19L per week)",
         "Premium (6 x 19L per week)", "Office bulk plan", "Family plan"]

ISSUES = [
    "the last delivery was short by two bottles",
    "two bottles in my last order were leaking",
    "my subscription plan was changed without notice",
    "I have not received this month's invoice",
    "the rider came after the scheduled window",
    "I want to move my delivery day from Wednesday to Friday",
    "the dispenser deposit was charged twice",
]

ACTIONS = [
    "Verified customer identity before changing the plan",
    "Escalated the billing dispute to accounts",
    "Updated the delivery address in the CRM",
    "Processed a refund for damaged bottles",
    "Renewed the subscription at customer request",
    "Scheduled a replacement dispenser",
]

URDU_PHRASES = ["شکریہ", "براہ کرم جلدی کریں", "پانی کی بوتلیں", "مہربانی"]


# ---------------------------------------------------------------------------
# Value generators: return (value, tags)
# ---------------------------------------------------------------------------

def _weighted(rng: random.Random, options: Sequence[Tuple[str, float]]) -> str:
    names = [o[0] for o in options]
    weights = [o[1] for o in options]
    return rng.choices(names, weights=weights, k=1)[0]


def gen_person(rng: random.Random) -> Tuple[str, Tuple[str, ...]]:
    first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
    tags: List[str] = []
    if rng.random() < 0.08:
        name = f"{first} {rng.choice(MIDDLE_NAMES)} {last}"
        tags.append("three_token_name")
    else:
        name = f"{first} {last}"
    r = rng.random()
    if r < 0.05:
        name = name.lower()
        tags.append("lowercase_name")
    elif r < 0.09:
        name = name.upper()
        tags.append("uppercase_name")
    return name, tuple(tags)


PHONE_FORMATS = [
    ("local_hyphen", 0.20), ("local_plain", 0.15), ("local_space", 0.10),
    ("intl_space", 0.12), ("intl_space_split", 0.08), ("intl_plain", 0.12),
    ("intl_hyphen", 0.08), ("intl00_hyphen", 0.06), ("intl00_space", 0.04),
    ("dot_separated", 0.03), ("local_4_3_4", 0.02),
]
HELDOUT_PHONE_FORMATS = {"dot_separated", "local_4_3_4"}


def format_phone(prefix: str, digits: str, fmt: str) -> str:
    return {
        "local_hyphen": f"0{prefix}-{digits}",
        "local_plain": f"0{prefix}{digits}",
        "local_space": f"0{prefix} {digits}",
        "intl_space": f"+92 {prefix} {digits}",
        "intl_space_split": f"+92 {prefix} {digits[:3]} {digits[3:]}",
        "intl_plain": f"+92{prefix}{digits}",
        "intl_hyphen": f"+92-{prefix}-{digits}",
        "intl00_hyphen": f"0092-{prefix}-{digits}",
        "intl00_space": f"0092 {prefix} {digits}",
        "dot_separated": f"0{prefix}.{digits}",
        "local_4_3_4": f"0{prefix} {digits[:3]} {digits[3:]}",
        "parenthesised": f"(0{prefix}) {digits}",
    }[fmt]


def gen_phone(rng: random.Random, fmt: Optional[str] = None) -> Tuple[str, Tuple[str, ...]]:
    fmt = fmt or _weighted(rng, PHONE_FORMATS)
    prefix = rng.choice(MOBILE_PREFIXES)
    digits = f"{rng.randint(0, 9999999):07d}"
    tags = [f"phone_{fmt}"]
    if fmt in HELDOUT_PHONE_FORMATS:
        tags.append("heldout_format")
    return format_phone(prefix, digits, fmt), tuple(tags)


def gen_cnic(rng: random.Random, fmt: Optional[str] = None) -> Tuple[str, Tuple[str, ...]]:
    fmt = fmt or _weighted(rng, [("hyphen", 0.62), ("plain", 0.33), ("spaced", 0.05)])
    a = rng.choice(CNIC_PREFIXES)
    b = f"{rng.randint(0, 9999999):07d}"
    c = str(rng.randint(1, 9))
    if fmt == "hyphen":
        return f"{a}-{b}-{c}", ("cnic_hyphen",)
    if fmt == "plain":
        return f"{a}{b}{c}", ("cnic_plain",)
    return f"{a} {b} {c}", ("cnic_spaced", "heldout_format")


def gen_email(rng: random.Random, name: Optional[str] = None) -> Tuple[str, Tuple[str, ...]]:
    if name is None:
        name = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
    parts = name.lower().split()
    first, last = parts[0], parts[-1]
    style = rng.randint(0, 3)
    n = rng.randint(1, 999)
    local = [f"{first}.{last}{n}", f"{first}{last}", f"{first[0]}.{last}", f"{first}_{last}{n}"][style]
    tags: List[str] = []
    if rng.random() < 0.05:
        local += "+water"
        tags.append("email_plus")
    email = f"{local}@{rng.choice(EMAIL_DOMAINS)}"
    if rng.random() < 0.04:
        email = email.upper()
        tags.append("uppercase_email")
    return email, tuple(tags)


def gen_customer_id(rng: random.Random) -> Tuple[str, Tuple[str, ...]]:
    value = f"UBW-{rng.randint(10000, 99999)}"
    if rng.random() < 0.05:
        return value.lower(), ("custid_lowercase",)
    return value, ()


def gen_postal(rng: random.Random) -> str:
    return str(rng.randint(10000, 99999))


ADDRESS_FORMATS = [
    ("house_street_block", 0.22), ("house_no_road", 0.18), ("h_no", 0.12),
    ("flat", 0.14), ("plot_sector", 0.10), ("shop", 0.07),
    ("abbrev_lower", 0.07), ("landmark", 0.10),
]


def gen_address(rng: random.Random, fmt: Optional[str] = None) -> Tuple[str, Tuple[str, ...]]:
    fmt = fmt or _weighted(rng, ADDRESS_FORMATS)
    city = rng.choice(CITIES)
    n = rng.randint(1, 999)
    tags = [f"addr_{fmt}"]
    if fmt == "house_street_block":
        value = (f"House #{n}, Street {rng.randint(1, 40)}, Block {rng.choice('ABCDEFGHJK')}, "
                 f"{rng.choice(LOCALITIES)}, {city}")
    elif fmt == "house_no_road":
        value = f"House No. {n}, {rng.choice(ROADS)}, {rng.choice(LOCALITIES)}, {city}"
    elif fmt == "h_no":
        value = f"H. No. {n}, {rng.choice(ROADS)}, {city}"
    elif fmt == "flat":
        value = (f"Flat {rng.randint(1, 20)}{rng.choice('ABCD')}, {rng.choice(BUILDINGS)}, "
                 f"{rng.choice(PHASES)}, {city}")
    elif fmt == "plot_sector":
        value = f"Plot {n}, Sector {rng.choice(ISLAMABAD_SECTORS)}, Islamabad"
    elif fmt == "shop":
        value = f"Shop {rng.randint(1, 80)}, {rng.choice(MARKETS)}, {city}"
    elif fmt == "abbrev_lower":
        value = (f"h no {n}, st {rng.randint(1, 40)}, {rng.choice(LOCALITIES).lower()}, "
                 f"{city.lower()}")
    else:  # landmark — held out from the custom address recogniser on purpose
        value = f"near {rng.choice(LANDMARKS)}, behind {rng.choice(MARKETS)}, {city}"
        tags.append("heldout_format")
    return value, tuple(tags)


# ---------------------------------------------------------------------------
# False-positive trap generators: return (value, kind, tags)
# ---------------------------------------------------------------------------

def gen_trap(rng: random.Random, kind: str) -> Tuple[str, str, Tuple[str, ...]]:
    if kind == "order_number":
        return f"ORD-2026-{rng.randint(0, 999999):06d}", kind, ()
    if kind == "order_digits":
        return f"{rng.randint(100000, 999999)}", kind, ()
    if kind == "invoice_total":
        return f"PKR {rng.randint(1, 49)},{rng.randint(0, 999):03d}", kind, ()
    if kind == "bottle_count":
        return f"{rng.randint(2, 40)} x 19L", kind, ()
    if kind == "date":
        d, m = rng.randint(1, 28), rng.randint(1, 12)
        style = rng.randint(0, 2)
        value = [f"2026-{m:02d}-{d:02d}", f"{d:02d}/{m:02d}/2026",
                 f"{d} {['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][m - 1]} 2026"][style]
        return value, kind, ()
    if kind == "batch_code":
        return f"BATCH-{rng.randint(1000, 9999)}-{rng.choice('ABCDEF')}", kind, ()
    if kind == "barcode":
        return f"896{rng.randint(0, 9999999999):010d}", kind, ("cnic_like",)
    if kind == "tracking_number":
        return f"{rng.choice('789')}{rng.randint(0, 9999999999):010d}", kind, ("phone_like",)
    if kind == "invoice_number":
        return f"{rng.randint(10000, 99999)}", kind, ("postal_like",)
    if kind == "vehicle_plate":
        return f"{rng.choice(['LEA', 'LEB', 'KHI', 'ISB', 'RIM'])}-{rng.randint(1000, 9999)}", kind, ()
    raise ValueError(kind)


# ---------------------------------------------------------------------------
# Small formatting helpers
# ---------------------------------------------------------------------------

def _sep(rng: random.Random) -> str:
    return rng.choice([": ", ": ", ": ", ":", " : ", " - "])


def _lab(rng: random.Random, label: str) -> str:
    r = rng.random()
    if r < 0.06:
        return label.upper()
    if r < 0.12:
        return label.lower()
    return label


def _nl(rng: random.Random) -> str:
    return rng.choice(["\n"] * 8 + ["\n\n", "  \n"])


def _maybe(rng: random.Random, p: float) -> bool:
    return rng.random() < p


PHONE_LABELS = ["Phone", "Mobile", "Contact", "Cell #", "Contact no.", "Ph", "Mob", "Tel", "WhatsApp"]
CNIC_LABELS = ["CNIC", "CNIC #", "CNIC No.", "NIC", "National ID", "National Identity Card", "Identity No.", "NADRA ID"]
EMAIL_LABELS = ["Email", "E-mail", "Email address", "Mail"]
ADDRESS_LABELS = ["Delivery Address", "Address", "Drop-off", "Service Address", "Deliver to"]
CUSTID_LABELS = ["Account ID", "Account", "Customer ID", "Acct", "Customer No."]
NAME_LABELS = ["Customer Name", "Name", "Full Name", "Customer"]


def _w_person(b: _DocBuilder, name: str, tags) -> Callable[[], None]:
    return lambda: b.pii(name, "PERSON", tags)


def _write_address(b: _DocBuilder, rng: random.Random, addr, addr_tags, postal: Optional[str]) -> None:
    """Address, optionally followed by an adjacent postal code after the city."""
    b.pii(addr, "ADDRESS", addr_tags)
    if postal is not None:
        b.t(rng.choice([" ", " - ", ", ", "-"]))
        b.pii(postal, "POSTAL_CODE", ("postal_after_city",))


def _form(b: _DocBuilder, rng: random.Random, fields: List[Tuple[str, Callable[[], None]]],
          shuffle: bool = True) -> None:
    """Write 'Label: value' lines in (optionally) shuffled order."""
    fields = list(fields)
    if shuffle:
        rng.shuffle(fields)
    for label, writer in fields:
        b.t(_lab(rng, label) + _sep(rng))
        writer()
        b.t(_nl(rng))


# ---------------------------------------------------------------------------
# Document builders (>= 3 phrasing variants per document type)
# ---------------------------------------------------------------------------

def _build_delivery_order(b: _DocBuilder, rng: random.Random) -> None:
    name, ntags = gen_person(rng)
    phone, ptags = gen_phone(rng)
    addr, atags = gen_address(rng)
    postal = gen_postal(rng)
    cid, ctags = gen_customer_id(rng)
    order, okind, otags = gen_trap(rng, rng.choice(["order_number", "order_digits"]))
    qty, qkind, qtags = gen_trap(rng, "bottle_count")
    variant = rng.randint(0, 2)

    if variant == 0:
        b.t(rng.choice(["DELIVERY ORDER", "Delivery Order", "NEW ORDER"]) + f" - {COMPANY_NAME}" + _nl(rng))
        b.t("Order Ref" + _sep(rng)).trap(order, okind, otags).t(_nl(rng))
        fields = [(rng.choice(NAME_LABELS), _w_person(b, name, ntags)),
                  (rng.choice(PHONE_LABELS), lambda: b.pii(phone, "PHONE_NUMBER", ptags))]
        postal_separate = _maybe(rng, 0.5)
        fields.append((rng.choice(ADDRESS_LABELS),
                       lambda: _write_address(b, rng, addr, atags, None if postal_separate else postal)))
        if postal_separate:
            fields.append((rng.choice(["Postal Code", "Postcode", "ZIP", "Postal code"]),
                           lambda: b.pii(postal, "POSTAL_CODE", ("postal_labelled",))))
        if _maybe(rng, 0.85):
            fields.append((rng.choice(CUSTID_LABELS), lambda: b.pii(cid, "CUSTOMER_ID", ctags)))
        _form(b, rng, fields)
        b.t("Quantity" + _sep(rng)).trap(qty, qkind, qtags).t(_nl(rng))
        if _maybe(rng, 0.6):
            total, tk, tt = gen_trap(rng, "invoice_total")
            b.t("Total" + _sep(rng)).trap(total, tk, tt).t(_nl(rng))
        b.t(rng.choice(["Instructions: leave bottles at the gate.",
                        "Instructions: ring the bell twice, do not call before 9 am.",
                        "Note: collect empty bottles."]))
    elif variant == 1:
        b.t("Order ").trap(order, okind, otags).t(" placed by ")
        b.pii(name, "PERSON", ntags)
        if _maybe(rng, 0.8):
            b.t(" (").pii(cid, "CUSTOMER_ID", ctags).t(")")
        b.t(" for ").trap(qty, qkind, qtags).t(" bottles. Deliver to ")
        _write_address(b, rng, addr, atags, postal if _maybe(rng, 0.5) else None)
        b.t(rng.choice([". Call ", ". Please call ", ". Rider should phone "]))
        b.pii(phone, "PHONE_NUMBER", ptags)
        b.t(" on arrival.")
        if _maybe(rng, 0.5):
            total, tk, tt = gen_trap(rng, "invoice_total")
            b.t(" Amount due ").trap(total, tk, tt).t(".")
    else:
        b.t(rng.choice(["new order!! ", "order pls - ", "Order via WhatsApp: "]))
        b.t("name ").pii(name, "PERSON", ntags).t(" | ")
        b.t(rng.choice(["ph ", "mob ", "no. "])).pii(phone, "PHONE_NUMBER", ptags).t(" | ")
        b.t("addr ")
        _write_address(b, rng, addr, atags, postal if _maybe(rng, 0.4) else None)
        b.t(" | ").trap(qty, qkind, qtags).t(" | ")
        b.t(rng.choice(["cash on delivery", "paid online", "card on delivery"]))


def _build_contact_form(b: _DocBuilder, rng: random.Random) -> None:
    name, ntags = gen_person(rng)
    email, etags = gen_email(rng, name)
    phone, ptags = gen_phone(rng)
    cnic, ctags = gen_cnic(rng)
    cid, cidtags = gen_customer_id(rng)
    variant = rng.randint(0, 2)

    if variant == 0:
        b.t("CONTACT FORM SUBMISSION" + _nl(rng))
        b.t(rng.choice(["Submitted", "Received"]) + _sep(rng))
        d, k, tg = gen_trap(rng, "date")
        b.trap(d, k, tg).t(_nl(rng))
        fields = [(rng.choice(["Full Name", "Name"]), _w_person(b, name, ntags)),
                  (rng.choice(EMAIL_LABELS), lambda: b.pii(email, "EMAIL_ADDRESS", etags))]
        if _maybe(rng, 0.85):
            fields.append((rng.choice(PHONE_LABELS), lambda: b.pii(phone, "PHONE_NUMBER", ptags)))
        if _maybe(rng, 0.7):
            fields.append((rng.choice(CNIC_LABELS), lambda: b.pii(cnic, "CNIC", ctags)))
        if _maybe(rng, 0.6):
            fields.append((rng.choice(CUSTID_LABELS), lambda: b.pii(cid, "CUSTOMER_ID", cidtags)))
        _form(b, rng, fields)
        b.t("Message" + _sep(rng) + rng.choice([
            "Please update my contact details.",
            "I want to pause deliveries for two weeks.",
            "Kindly send a new dispenser."]))
    elif variant == 1:
        b.t(rng.choice(["Hi, this is ", "Hello, my name is ", "Assalam o Alaikum, I am "]))
        b.pii(name, "PERSON", ntags)
        b.t(rng.choice([". My email is ", ". You can write to ", ". Email me at "]))
        b.pii(email, "EMAIL_ADDRESS", etags)
        b.t(rng.choice([" and my number is ", ", phone ", " or call "]))
        b.pii(phone, "PHONE_NUMBER", ptags)
        b.t(". ")
        if _maybe(rng, 0.8):
            if _maybe(rng, 0.85):
                b.t(rng.choice(["My CNIC is ", "For verification, CNIC ", "National ID: ",
                                "my identity card number is "]))
                b.pii(cnic, "CNIC", ctags)
            else:
                b.t(rng.choice(["Please verify me with ", "Use this for verification: "]))
                b.pii(cnic, "CNIC", ctags + ("no_context",))
            b.t(". ")
        b.t(rng.choice(["I would like to upgrade my plan.", "Thanks.", "Please call back."]))
    else:
        b.t("form_id=web-contact; ")
        b.t("name=").pii(name, "PERSON", ntags).t("; ")
        b.t("email=").pii(email, "EMAIL_ADDRESS", etags).t("; ")
        if _maybe(rng, 0.8):
            b.t("phone=").pii(phone, "PHONE_NUMBER", ptags).t("; ")
        if _maybe(rng, 0.5):
            b.t("cnic=").pii(cnic, "CNIC", ctags).t("; ")
        b.t("topic=" + rng.choice(["billing", "delivery", "new connection"]))


def _build_subscription_record(b: _DocBuilder, rng: random.Random) -> None:
    name, ntags = gen_person(rng)
    email, etags = gen_email(rng, name)
    addr, atags = gen_address(rng)
    postal = gen_postal(rng)
    cid, ctags = gen_customer_id(rng)
    plan = rng.choice(PLANS)
    variant = rng.randint(0, 2)

    if variant == 0:
        b.t(f"SUBSCRIPTION RECORD - {COMPANY_NAME}" + _nl(rng))
        postal_separate = _maybe(rng, 0.5)
        fields = [("Subscriber", _w_person(b, name, ntags)),
                  (rng.choice(CUSTID_LABELS), lambda: b.pii(cid, "CUSTOMER_ID", ctags)),
                  ("Plan", lambda: b.t(plan)),
                  (rng.choice(["Billing Email", "Email"]), lambda: b.pii(email, "EMAIL_ADDRESS", etags)),
                  ("Service Address",
                   lambda: _write_address(b, rng, addr, atags, None if postal_separate else postal))]
        if postal_separate:
            fields.append(("Postal Code", lambda: b.pii(postal, "POSTAL_CODE", ("postal_labelled",))))
        _form(b, rng, fields)
        d, k, tg = gen_trap(rng, "date")
        b.t("Start date" + _sep(rng)).trap(d, k, tg).t(_nl(rng))
        b.t("Status: " + rng.choice(["Active", "Paused", "Pending renewal"]))
    elif variant == 1:
        b.t("SUB | ").pii(cid, "CUSTOMER_ID", ctags).t(" | ")
        b.pii(name, "PERSON", ntags).t(" | " + plan + " | ")
        b.pii(email, "EMAIL_ADDRESS", etags).t(" | ")
        _write_address(b, rng, addr, atags, postal if _maybe(rng, 0.6) else None)
        inv, k, tg = gen_trap(rng, "invoice_number")
        b.t(" | last invoice ").trap(inv, k, tg)
    else:
        b.pii(name, "PERSON", ntags)
        d, k, tg = gen_trap(rng, "date")
        b.t(f" renewed the {plan} on ").trap(d, k, tg)
        b.t(" for account ").pii(cid, "CUSTOMER_ID", ctags).t(". ")
        b.t(rng.choice(["Invoices go to ", "Billing contact: ", "Send receipts to "]))
        b.pii(email, "EMAIL_ADDRESS", etags).t(". ")
        if _maybe(rng, 0.7):
            b.t("Bottles are delivered to ")
            _write_address(b, rng, addr, atags, None)
            if _maybe(rng, 0.5):
                b.t(", postal code ").pii(postal, "POSTAL_CODE", ("postal_labelled",))
            b.t(".")


def _build_delivery_note(b: _DocBuilder, rng: random.Random) -> None:
    driver, dtags = gen_person(rng)
    recipient, rtags = gen_person(rng)
    while recipient.lower() == driver.lower():
        recipient, rtags = gen_person(rng)
    phone, ptags = gen_phone(rng)
    addr, atags = gen_address(rng)
    qty, qk, qt = gen_trap(rng, "bottle_count")
    plate, pk, pt = gen_trap(rng, "vehicle_plate")
    variant = rng.randint(0, 2)

    if variant == 0:
        b.t("DELIVERY NOTE" + _nl(rng))
        fields = [("Driver", _w_person(b, driver, dtags)),
                  ("Recipient", _w_person(b, recipient, rtags)),
                  (rng.choice(["Recipient Phone", "Phone", "Contact"]),
                   lambda: b.pii(phone, "PHONE_NUMBER", ptags)),
                  (rng.choice(["Drop-off", "Address", "Deliver to"]),
                   lambda: _write_address(b, rng, addr, atags, None)),
                  ("Units", lambda: b.trap(qty, qk, qt)),
                  ("Vehicle", lambda: b.trap(plate, pk, pt))]
        _form(b, rng, fields)
        b.t("Signature required: " + rng.choice(["Yes", "No"]))
    elif variant == 1:
        b.t("Driver ").pii(driver, "PERSON", dtags)
        b.t(" delivered ").trap(qty, qk, qt).t(" to ")
        b.pii(recipient, "PERSON", rtags).t(" at ")
        _write_address(b, rng, addr, atags, None)
        b.t(rng.choice([". Recipient phone ", ". Customer mobile: ", ". Contact "]))
        b.pii(phone, "PHONE_NUMBER", ptags).t(". ")
        batch, k, tg = gen_trap(rng, "batch_code")
        b.t("Batch ").trap(batch, k, tg).t(", van ").trap(plate, pk, pt).t(".")
    else:
        dn, k, tg = gen_trap(rng, "order_digits")
        b.t("DN-").trap(dn, k, tg).t(" | drv: ").pii(driver, "PERSON", dtags)
        b.t(" | to: ").pii(recipient, "PERSON", rtags).t(" | ")
        b.pii(phone, "PHONE_NUMBER", ptags).t(" | ")
        _write_address(b, rng, addr, atags, None)
        b.t(" | ").trap(qty, qk, qt)


def _build_customer_service_message(b: _DocBuilder, rng: random.Random) -> None:
    name, ntags = gen_person(rng)
    email, etags = gen_email(rng, name)
    phone, ptags = gen_phone(rng)
    cid, ctags = gen_customer_id(rng)
    issue = rng.choice(ISSUES)
    urdu = _maybe(rng, 0.10)
    utag = ("unicode_context",) if urdu else ()
    variant = rng.randint(0, 2)

    if variant == 0:
        b.t("From: ").pii(name, "PERSON", ntags + utag).t(" <").pii(email, "EMAIL_ADDRESS", etags + utag).t(">\n")
        b.t("Subject: " + rng.choice(["Complaint", "Delivery issue", "Billing question"]) + "\n")
        if _maybe(rng, 0.8):
            b.t(_lab(rng, "Account") + _sep(rng)).pii(cid, "CUSTOMER_ID", ctags + utag).t("\n")
        if _maybe(rng, 0.8):
            b.t(_lab(rng, rng.choice(["Call-back", "Phone", "Mobile"])) + _sep(rng))
            b.pii(phone, "PHONE_NUMBER", ptags + utag).t("\n")
        b.t(f"\nHello support team,\n\nI am writing to report that {issue}. ")
        if urdu:
            b.t(rng.choice(URDU_PHRASES) + ". ")
        b.t("Please look into this.\n\n" + rng.choice(["Regards", "Thanks", "Sincerely"]) + ",\n")
        b.pii(name, "PERSON", ntags + utag + ("repeated_value",))
    elif variant == 1:
        b.t(rng.choice(["Customer: ", "Chat transcript - customer: "]))
        b.t(f"salam, {issue}. ")
        if urdu:
            b.t(rng.choice(URDU_PHRASES) + " ")
        b.t(rng.choice(["my number is ", "call me on ", "reach me at "]))
        b.pii(phone, "PHONE_NUMBER", ptags + utag)
        b.t(rng.choice([" and email ", ", email: ", " or mail "]))
        b.pii(email, "EMAIL_ADDRESS", etags + utag)
        b.t("\nAgent: Thanks, may I have your name and account?\nCustomer: ")
        b.pii(name, "PERSON", ntags + utag).t(", ")
        b.pii(cid, "CUSTOMER_ID", ctags + utag)
    else:
        tk, k, tg = gen_trap(rng, "order_digits")
        b.t("Ticket #").trap(tk, k, tg).t(" opened by ")
        b.pii(name, "PERSON", ntags + utag)
        b.t(". Contact: ").pii(email, "EMAIL_ADDRESS", etags + utag)
        if _maybe(rng, 0.7):
            b.t(" / ").pii(phone, "PHONE_NUMBER", ptags + utag)
        b.t(f". Issue: {issue}.")
        if urdu:
            b.t(" " + rng.choice(URDU_PHRASES))


def _build_internal_note(b: _DocBuilder, rng: random.Random) -> None:
    staff, stags = gen_person(rng)
    customer, ctags = gen_person(rng)
    cid, cidtags = gen_customer_id(rng)
    phone, ptags = gen_phone(rng)
    cnic, cntags = gen_cnic(rng)
    variant = rng.choices([0, 1, 2], weights=[0.45, 0.40, 0.15], k=1)[0]

    if variant == 0:
        b.t(f"INTERNAL OPERATIONAL NOTE - {COMPANY_NAME}" + _nl(rng))
        fields = [("Handled by", _w_person(b, staff, stags)),
                  ("Customer Account", lambda: b.pii(cid, "CUSTOMER_ID", cidtags))]
        if _maybe(rng, 0.8):
            fields.append(("Customer " + rng.choice(["CNIC", "NIC", "National ID"]),
                           lambda: b.pii(cnic, "CNIC", cntags)))
        if _maybe(rng, 0.8):
            fields.append(("Customer callback", lambda: b.pii(phone, "PHONE_NUMBER", ptags)))
        _form(b, rng, fields)
        b.t("Action: " + rng.choice(ACTIONS) + _nl(rng))
        ref, k, tg = gen_trap(rng, rng.choice(["order_number", "batch_code", "invoice_number"]))
        b.t("Reference: ").trap(ref, k, tg).t(_nl(rng))
        b.t("Confidential - not for external distribution.")
    elif variant == 1:
        b.t(rng.choice(["Spoke with ", "Call from ", "Visited "]))
        b.pii(customer, "PERSON", ctags)
        b.t(" today about account ").pii(cid, "CUSTOMER_ID", cidtags).t(". ")
        if _maybe(rng, 0.85):
            b.t(rng.choice(["Verified CNIC ", "Checked national ID ", "NIC on file "]))
            b.pii(cnic, "CNIC", cntags).t(". ")
        else:
            b.t("Customer read out ").pii(cnic, "CNIC", cntags + ("no_context",)).t(" for verification. ")
        b.t("Will call back on ").pii(phone, "PHONE_NUMBER", ptags).t(". - ")
        b.pii(staff, "PERSON", stags)
    else:
        # Shift log: no PII, traps only
        d, k, tg = gen_trap(rng, "date")
        b.t("Shift report ").trap(d, k, tg).t(": ")
        q, k2, t2 = gen_trap(rng, "bottle_count")
        b.trap(q, k2, t2).t(" dispatched, batch ")
        bc, k3, t3 = gen_trap(rng, "batch_code")
        b.trap(bc, k3, t3).t(" passed QC, van ")
        vp, k4, t4 = gen_trap(rng, "vehicle_plate")
        b.trap(vp, k4, t4).t(" serviced. Pallet barcode ")
        bar, k5, t5 = gen_trap(rng, "barcode")
        b.trap(bar, k5, t5).t(", courier tracking ")
        tr, k6, t6 = gen_trap(rng, "tracking_number")
        b.trap(tr, k6, t6).t(". Petty cash ")
        tot, k7, t7 = gen_trap(rng, "invoice_total")
        b.trap(tot, k7, t7).t(".")


BUILDERS = {
    "delivery_order": _build_delivery_order,
    "contact_form": _build_contact_form,
    "subscription_record": _build_subscription_record,
    "delivery_note": _build_delivery_note,
    "customer_service_message": _build_customer_service_message,
    "internal_operational_note": _build_internal_note,
}


# ---------------------------------------------------------------------------
# Challenge records (deliberately hard cases), built with the same builder
# ---------------------------------------------------------------------------

def _challenge_specs() -> List[Tuple[str, Callable[[_DocBuilder, random.Random], None]]]:
    def c_cnic_plain_sentence(b, rng):
        v, t = gen_cnic(rng, "plain")
        b.t("Please find the verification attached. My identity number is ")
        b.pii(v, "CNIC", t + ("challenge",)).t(" as per NADRA records.")

    def c_phone_long_sentence(b, rng):
        v, t = gen_phone(rng, "local_hyphen")
        b.t("Kindly note that I will be travelling for most of next week and the gate will be locked, "
            "so the rider should not leave the bottles outside but instead reach out to me on ")
        b.pii(v, "PHONE_NUMBER", t + ("long_sentence",))
        b.t(" between 10 am and 5 pm on any weekday so that my neighbour can receive the order.")

    def c_name_possessive(b, rng):
        first = rng.choice(FIRST_NAMES)
        b.pii(first, "PERSON", ("single_token_name", "possessive"))
        b.t("'s delivery was moved to Friday. ")
        full = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        b.t("Mr.").pii(full, "PERSON", ("no_space_title",)).t(" approved the change.")

    def c_email_brackets(b, rng):
        e1, t1 = gen_email(rng)
        e2, t2 = gen_email(rng)
        b.t("Send the invoice copy to (").pii(e1, "EMAIL_ADDRESS", t1 + ("email_parentheses",))
        b.t(") and cc <").pii(e2, "EMAIL_ADDRESS", t2 + ("email_angle",)).t(">.")

    def c_multi_short(b, rng):
        n, nt = gen_person(rng)
        c, ct = gen_cnic(rng, "hyphen")
        p, pt = gen_phone(rng, "intl_plain")
        b.t("Record for ").pii(n, "PERSON", nt).t(": CNIC ").pii(c, "CNIC", ct)
        b.t(", mobile ").pii(p, "PHONE_NUMBER", pt).t(".")

    def c_barcode_trap(b, rng):
        bar, k, t = gen_trap(rng, "barcode")
        b.t("Product barcode scanned: ").trap(bar, k, t).t(". No personal data in this record.")

    def c_intl00_sentence(b, rng):
        v, t = gen_phone(rng, "intl00_hyphen")
        b.t("Alternative contact provided by the customer: ").pii(v, "PHONE_NUMBER", t).t(".")

    def c_nested_postal(b, rng):
        n, nt = gen_person(rng)
        e, et = gen_email(rng, n)
        b.t("Subscriber ").pii(n, "PERSON", nt).t(" at ")
        b.open("ADDRESS", ("addr_flat", "nested"))
        b.t(f"Flat {rng.randint(1, 9)}B, {rng.choice(PHASES)}, Karachi - ")
        b.pii(gen_postal(rng), "POSTAL_CODE", ("nested",))
        b.close()
        b.t(".\nContact email: ").pii(e, "EMAIL_ADDRESS", et).t(".")

    def c_upper_email(b, rng):
        e, t = gen_email(rng)
        b.t("EMAIL ON RECORD: ").pii(e.upper(), "EMAIL_ADDRESS", ("uppercase_email",)).t(". PLEASE VERIFY.")

    def c_traps_only(b, rng):
        b.t("System health report. Order ")
        o, k, t = gen_trap(rng, "order_number")
        b.trap(o, k, t).t(" synced. Invoice ")
        i, k2, t2 = gen_trap(rng, "invoice_number")
        b.trap(i, k2, t2).t(" total ")
        tot, k3, t3 = gen_trap(rng, "invoice_total")
        b.trap(tot, k3, t3).t(". Tracking ")
        tr, k4, t4 = gen_trap(rng, "tracking_number")
        b.trap(tr, k4, t4).t(". Next maintenance ")
        d, k5, t5 = gen_trap(rng, "date")
        b.trap(d, k5, t5).t(". No customer data processed.")

    def c_same_phone_twice(b, rng):
        v, t = gen_phone(rng, "local_plain")
        b.t("Primary contact ").pii(v, "PHONE_NUMBER", t + ("repeated_value",))
        b.t(". If unreachable, try ").pii(v, "PHONE_NUMBER", t + ("repeated_value",))
        b.t(" again after 6 pm.")

    def c_start_end(b, rng):
        p, pt = gen_phone(rng, "intl_space")
        e, et = gen_email(rng)
        b.pii(p, "PHONE_NUMBER", pt + ("at_text_start",))
        b.t(" called about a missing delivery; reply by email to ")
        b.pii(e, "EMAIL_ADDRESS", et + ("at_text_end",))

    def c_cnic_no_context(b, rng):
        v, t = gen_cnic(rng, "plain")
        b.t("Customer read out ").pii(v, "CNIC", t + ("no_context",)).t(" twice on the call.")

    def c_phone_parenthesised(b, rng):
        v, t = gen_phone(rng, "parenthesised")
        b.t("Rider said the gate guard can be reached at ").pii(v, "PHONE_NUMBER", t).t(" after dark.")

    def c_lowercase_name(b, rng):
        n = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}".lower()
        b.t("spoke to ").pii(n, "PERSON", ("lowercase_name",)).t(" about the leaking dispenser, will revisit.")

    def c_landmark_address(b, rng):
        a, t = gen_address(rng, "landmark")
        b.t("Please drop the bottles ").pii(a, "ADDRESS", t).t(" - the house with the green gate.")

    def c_cnic_spaced(b, rng):
        v, t = gen_cnic(rng, "spaced")
        b.t("CNIC: ").pii(v, "CNIC", t).t(" (customer typed it with spaces).")

    def c_urdu_phone(b, rng):
        v, t = gen_phone(rng, "local_hyphen")
        b.t("براہ کرم ").pii(v, "PHONE_NUMBER", t + ("unicode_context",)).t(" پر کال کریں۔ شکریہ")

    def c_no_spaces(b, rng):
        n = f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"
        p, pt = gen_phone(rng, "local_hyphen")
        b.t("Contact:").pii(n, "PERSON", ("no_whitespace",)).t("(").pii(p, "PHONE_NUMBER", pt + ("no_whitespace",)).t(")")

    def c_accented_name(b, rng):
        e, et = gen_email(rng)
        b.t("Customer Name: ").pii("Zoë Ahmed", "PERSON", ("accented_name",))
        b.t(", café order, email ").pii(e, "EMAIL_ADDRESS", et).t(".")

    return [
        ("customer_service_message", c_phone_long_sentence),
        ("contact_form", c_cnic_plain_sentence),
        ("delivery_note", c_name_possessive),
        ("customer_service_message", c_email_brackets),
        ("internal_operational_note", c_multi_short),
        ("delivery_order", c_barcode_trap),
        ("contact_form", c_intl00_sentence),
        ("subscription_record", c_nested_postal),
        ("contact_form", c_upper_email),
        ("internal_operational_note", c_traps_only),
        ("customer_service_message", c_same_phone_twice),
        ("customer_service_message", c_start_end),
        ("internal_operational_note", c_cnic_no_context),
        ("delivery_note", c_phone_parenthesised),
        ("internal_operational_note", c_lowercase_name),
        ("delivery_order", c_landmark_address),
        ("contact_form", c_cnic_spaced),
        ("customer_service_message", c_urdu_phone),
        ("delivery_note", c_no_spaces),
        ("delivery_order", c_accented_name),
    ]


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def generate_dataset_full(seed: int = 42, count: int = 850
                          ) -> Tuple[List[SyntheticRecord], List[PlantedEntity], List[TrapAnnotation]]:
    """Generate ``count`` planted records plus the fixed challenge records.

    Deterministic for a given (seed, count). Every record text is unique.
    Returns (records, ground_truth, traps).
    """
    if count < 1:
        raise ValueError("count must be >= 1")
    rng = random.Random(seed)
    records: List[SyntheticRecord] = []
    seen = set()

    for i in range(count):
        record_id = f"REC-{i + 1:05d}"
        doc_type = DOC_TYPES[i % len(DOC_TYPES)]
        for _attempt in range(20):
            b = _DocBuilder(record_id, doc_type, "planted")
            BUILDERS[doc_type](b, rng)
            rec = b.build()
            if rec.text not in seen:
                break
        else:
            raise RuntimeError(f"Could not generate a unique text for {record_id}")
        seen.add(rec.text)
        records.append(rec)

    for j, (doc_type, fn) in enumerate(_challenge_specs()):
        b = _DocBuilder(f"CHAL-{j + 1:03d}", doc_type, "challenge")
        fn(b, rng)
        rec = b.build()
        if rec.text in seen:
            raise RuntimeError(f"Duplicate challenge text {rec.record_id}")
        seen.add(rec.text)
        records.append(rec)

    ground_truth = [e for r in records for e in r.planted_entities]
    traps = [t for r in records for t in r.traps]
    return records, ground_truth, traps


def generate_dataset(seed: int = 42, count: int = 850
                     ) -> Tuple[List[SyntheticRecord], List[PlantedEntity]]:
    """Backward-compatible wrapper returning (records, ground_truth)."""
    records, gt, _ = generate_dataset_full(seed=seed, count=count)
    return records, gt
