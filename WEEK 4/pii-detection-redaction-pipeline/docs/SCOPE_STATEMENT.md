# Scope Statement
## PII Detection & Redaction Pipeline
### Urban Bottled Water Company (Fictional)
### Week 4 Specialist Advanced Project — Member 5

---

## 1. Business Context

The Urban Bottled Water Company (fictional) processes daily business records: customer delivery orders, customer contact forms, subscription records, delivery notes and delivery instructions, customer-service messages, and internal operational notes. These documents routinely contain personal information about customers and staff.

When such records are shared for analytics, reporting, QA testing, or downstream AI-assisted processing, they must first be screened for personal information that would otherwise be exposed unnecessarily. This project builds and evaluates a reproducible, locally run PII detection and redaction pipeline (Microsoft Presidio) and measures how much of the planted PII it actually finds.

---

## 2. In-Scope Information

### Direct identifiers
On their own they point to one specific person (or their home).

| Category | Description | Synthetic example |
|---|---|---|
| `PERSON` | Person names (customers, recipients, drivers, staff) | Ayesha Khan |
| `PHONE_NUMBER` | Pakistani mobile numbers in local and international formats | 0321-1234567, +92 321 1234567 |
| `CNIC` | Pakistani CNIC-style identity numbers, with and without separators | 42101-1234567-1, 4210112345671 |
| `EMAIL_ADDRESS` | Email addresses | ayesha.khan12@example.org |
| `ADDRESS` | Street / delivery addresses at house, flat, plot or shop level | House #12, Street 4, Block B, Gulberg, Lahore |

### Contextual / quasi-identifiers
They narrow identification when combined with other data, or identify a person inside company systems.

| Category | Description | Synthetic example |
|---|---|---|
| `POSTAL_CODE` | 5-digit Pakistani postal codes | 54000 |
| `CUSTOMER_ID` | Urban Bottled Water account identifiers. Classified as potentially identifying under the privacy policy because they are internal linkage keys: anyone with CRM access can map them to a person. | UBW-12345 |

### Expected-handling categories (used in the ground truth)

| Category | Meaning |
|---|---|
| `REDACT` | Planted PII occurrence; must be detected and replaced |
| `KEEP` | Annotated false-positive trap (order numbers, bottle counts, invoice totals, dates, batch codes, barcodes, tracking numbers, vehicle plates). Not PII; should survive redaction unchanged |

All values are fictional. Email addresses use only the reserved domains `example.com`, `example.org`, `example.net` (RFC 2606). Phone and CNIC values are random digits in the documented formats; they are not checked against, or derived from, any real register.

---

## 3. Out of Scope

- Real customer records, real CNICs, real phone numbers, real email addresses.
- Medical, financial, or other unrelated datasets.
- Production deployment.
- Claims of legal compliance, certification, or guaranteed anonymity.
- Automatically determining the identity of real individuals.
- Guaranteeing zero residual PII. Automated detection is fallible; human review is required before sharing high-risk output.

---

## 4. Intended Users

| Role | Purpose |
|---|---|
| Privacy or compliance reviewers | Assess detection quality and coverage |
| Data analysts | Prepare documents for analytics without exposing PII |
| Developers | Prepare documents for downstream processing and testing |
| Authorised staff | Review redaction quality before documents are shared |

---

## 5. Success Criteria (defined before the final evaluation)

### 5.1 Deliverable criteria

| Criterion | Target |
|---|---|
| Synthetic records | ≥ 800 unique records (fixed seed 42) |
| PII categories | ≥ 6 distinct types (plan: 7) |
| Ground-truth annotations | 100% of planted occurrences annotated and offset-validated |
| Baseline pipeline | Default Presidio recognisers, evaluated on the full dataset |
| Improved pipeline | Presidio + custom recognisers, evaluated on the same dataset, ground truth and seed |
| Metrics | Precision, recall and F1 for every supported category |
| Dangerous misses | 15 cases reviewed (actual misses; clearly labelled constructed cases only if fewer than 15 actual misses exist) |
| Automated tests | Implemented and run; results reported as observed |
| Privacy policy | Completed |
| Peer review | Template ready; the real classmate review is a user action (PENDING until done) |
| Final report | Reproducible from the scripts in this repository |

### 5.2 Initial numeric targets — Improved pipeline (Experiment B)

Exact-span, entity-level matching (see the evaluation report for the matching rules).

| Entity | Recall target | Precision target |
|---|---|---|
| `PHONE_NUMBER` | ≥ 0.85 | ≥ 0.90 |
| `CNIC` | ≥ 0.80 | ≥ 0.90 |
| `EMAIL_ADDRESS` | ≥ 0.90 | ≥ 0.95 |
| `CUSTOMER_ID` | ≥ 0.95 | ≥ 0.95 |
| `PERSON` | ≥ 0.50 | ≥ 0.60 |
| `ADDRESS` | ≥ 0.40 | ≥ 0.50 |
| `POSTAL_CODE` | ≥ 0.60 | ≥ 0.80 |

Additional targets:

| Criterion | Target |
|---|---|
| Overall improved recall | ≥ 0.75 |
| Direct-identifier regression | Improved recall ≥ baseline recall for `PHONE_NUMBER` and `CNIC` |
| False-positive trap hit rate (improved) | ≤ 10% of annotated traps |
| Residual planted direct identifiers (`PHONE_NUMBER`, `CNIC`, `EMAIL_ADDRESS`) after improved redaction | ≤ 5% of their ground-truth count |
| Test suite | Full pytest suite passes with 0 failures |

The baseline (Experiment A) has no numeric targets. It is the measured reference.

These targets are aspirational. Results that miss them are reported as misses; targets are not moved after the results are known.

Where the results stand against these targets:

- **Initial run** (`output/metrics/initial/`): missed PERSON precision, EMAIL_ADDRESS recall and precision, and the FP-trap rate.
- **Final run** (`output/metrics/comparison.csv`): meets all of them, with the in-sample caveat explained in `docs/EVALUATION_REPORT.md` Section 8.

The targets above are unchanged.

### 5.3 Target history

| Date | Change | Reason |
|---|---|---|
| Before implementation | Recall targets for the seven entity types recorded | Initial scope |
| 2026-10-06 (before any dataset-level evaluation was run) | Precision targets, overall recall, direct-identifier regression, FP-trap rate and residual targets added; recall targets unchanged | The original list had recall only. Precision and residual targets are needed to judge redaction quality. No metrics existed when they were added. |

---

## 6. Constraints

- Windows 11, Python 3.13.5, 8 GB RAM, limited free disk.
- No GPU, no paid API, no Docker, no database, no large language model or Transformer model.
- Small spaCy model `en_core_web_sm` only (the Presidio default `en_core_web_lg` is not installed or used).
- All processing runs locally; no document content is transmitted externally.
- Synthetic data only; no real PII is stored or processed.
