# Privacy Policy
## Urban Bottled Water Company (fictional): PII Detection & Redaction Pipeline
**Version 1.1 | October 2026 | Status: technical prototype**

> **Governance notice.** This document describes the intended privacy-handling policy for this prototype. It is a technical design document, not a legal compliance statement. The pipeline does not certify compliance with any privacy law or regulation. Any operational use would first need review by qualified legal and privacy professionals.

---

## 1. Purpose and scope

### 1.1 Why the pipeline exists
Urban Bottled Water Company records may contain personal information:

- delivery orders and delivery notes
- contact forms
- subscription records
- customer-service messages
- internal operational notes

Before these records are used for analytics, software testing, AI-assisted processing or reporting, any personal information those uses do not need must be removed. The pipeline detects that information and replaces it automatically. Its measured detection quality is published in `docs/EVALUATION_REPORT.md`.

### 1.2 Personal data covered
The classification below matches `docs/SCOPE_STATEMENT.md`.

| Category | Pipeline label | Classification |
|---|---|---|
| Person name | `PERSON` | Direct identifier |
| Pakistani mobile number | `PHONE_NUMBER` | Direct identifier |
| CNIC-style identity number | `CNIC` | Direct identifier |
| Email address | `EMAIL_ADDRESS` | Direct identifier |
| Street / delivery address (house, flat, plot or shop level) | `ADDRESS` | Direct identifier |
| 5-digit postal code | `POSTAL_CODE` | Contextual / quasi-identifier |
| Company account id (`UBW-ddddd`) | `CUSTOMER_ID` | Contextual / quasi-identifier. It is an internal linkage key: anyone with CRM access can map it to a person. |

### 1.3 Not covered
- Medical, financial, passport or biometric data.
- Order numbers, invoice numbers, batch codes, barcodes, vehicle plates and similar operational codes. These are not personal data. They are used as false-positive traps in the evaluation.
- Real customer records. This prototype processes only synthetic data.

---

## 2. Data minimisation

- **Analytics exports:** remove all direct identifiers and keep only the attributes the analysis needs.
- **Testing:** use synthetic records. The pipeline refuses dataset files without a `synthetic=true` column. It also refuses text containing email addresses outside `example.com` / `example.org` / `example.net` (`privacy.assert_synthetic_text`, CLI exit code 2). This is a tripwire, not proof that the data is synthetic.
- **Logs:** record ids, counts, labels, paths and timings only (see Section 6).
- **Evaluation:** ground truth comes from the generator at construction time, never from real records or detector output.
- **No real files:** staff must not import real customer files for testing or experimentation.

---

## 3. Processing location

All processing runs on the local machine:

- No document content is sent to external APIs, cloud services or remote models.
- The NLP model (`en_core_web_sm`) is installed locally from a pinned wheel. The pipeline refuses to start rather than download a different model at runtime.
- Presidio's email recogniser uses `tldextract`, whose default extractor may fetch the public-suffix list online. The pipeline replaces that extractor with one that uses only the bundled snapshot.
- `tests/test_privacy.py::test_analysis_makes_no_network_connections` and `test_no_eval_exec_or_network_imports_in_src` check this. These tests cover the code paths they exercise. They do not prove the absence of every possible network call by third-party libraries.

If the pipeline is ever changed to use a remote service, this section must be updated and approved by the privacy owner first.

---

## 4. Retention schedule (proposed)

These are proposed periods for a prototype. They are not a legal records-retention schedule.

| Artifact | Location | Proposed retention |
|---|---|---|
| Raw input documents (synthetic) | `data/generated/` | Regenerable from seed 42. Keep while the project is active; delete or regenerate on demand. Real raw input would be deleted after processing, within 30 days at most. |
| Ground-truth annotations and traps | `data/generated/` | Project lifetime (needed for reproducible evaluation) |
| Redacted output | `output/redacted/` (git-ignored) | Only as long as the downstream purpose needs it, then delete. Redacted output is still treated with care because residual PII is possible. |
| Predictions (spans, labels, scores, no text) | `output/predictions/` | Project lifetime |
| Metrics, charts, reports | `output/metrics/`, `output/charts/`, `docs/` | 12 months after project close |
| Diagnostic logs | `output/pipeline.log` (git-ignored) | 90 days, or delete after each review session |
| Configuration | `config/settings.json` | Project lifetime |

---

## 5. Access control

| Artifact | Who may access |
|---|---|
| Original documents (even synthetic) | Pipeline operators and privacy/compliance reviewers |
| Ground-truth annotations | Pipeline engineers and compliance reviewers |
| Redacted output | Downstream consumers approved by the data owner |
| Metrics and reports | Analytics, compliance and engineering staff |
| Configuration and the HMAC key | Pipeline operators/administrators only. The key is never committed. |
| Logs | Administrators and the privacy owner |

Technical separation:

- Originals, annotations and redacted output live in separate directory trees (`privacy.validate_output_dir_separation`).
- `redact --output` must point inside `output/redacted/`.
- `redact --file` must point inside `data/`.

This prototype has no user authentication. Any shared deployment would need operating-system or application-level access control.

---

## 6. Logging

**Raw personal information must not appear in ordinary log messages or error output.**

- Pipeline code logs only record ids, counts, labels, paths and timings. `logging.log_raw_text` in `config/settings.json` is `false`.
- When the anonymizer fails, the error log contains only the record id and the exception type, never the text.
- A second line of defence, `privacy.RawTextRedactingFilter`, is attached to the `pii_pipeline` logger and its handlers. It masks email-like, CNIC-like, `UBW-` id and long digit-run strings in every log record.
- Dry-run previews and reports show masked values (`privacy.mask_value`: first and last two characters only).
- Tests write their logs to a temporary file, not to `output/pipeline.log` (`tests/conftest.py`).

**Protected debugging (exception procedure).** If raw values are genuinely needed to debug a detection:

1. The privacy owner approves the session in advance.
2. The session uses synthetic data only, on a local machine, with the log written outside the repository.
3. The log file is treated as sensitive and deleted at the end of the session.
4. The session (date, purpose, who) is recorded without the values themselves.

`logging.log_raw_text` is read into `config.LOG_RAW_TEXT`, but no code path logs raw text, so setting it to `true` changes nothing. Debugging with raw values would require a local, uncommitted code change, which must be reverted afterwards.

---

## 7. Masking, hashing and pseudonymisation

### 7.1 Replacement (primary method)
Detected spans are replaced with type placeholders by Presidio's `AnonymizerEngine`:

| Label | Placeholder |
|---|---|
| PERSON | `[PERSON]` |
| PHONE_NUMBER | `[PHONE]` |
| CNIC | `[CNIC]` |
| EMAIL_ADDRESS | `[EMAIL]` |
| ADDRESS | `[ADDRESS]` |
| POSTAL_CODE | `[POSTAL_CODE]` |
| CUSTOMER_ID | `[CUSTOMER_ID]` |
| any other label | `[REDACTED]` |

**When to use it:** whenever downstream users do not need to link records about the same person. This is the default.

**Limitation:** quasi-identifiers that remain in the text, such as an area, delivery day or bottle count, may still narrow down a person. Replacement only covers what was detected.

### 7.2 Keyed one-way digest (limited matching)
`privacy.keyed_pseudonym(value)` computes **HMAC-SHA256**. The key is read from the `PII_PIPELINE_HMAC_KEY` environment variable; `.env.example` holds only a placeholder. The function raises an error if no key is set.

**When to use it:** an analyst needs to know that two records refer to the same account or phone number without seeing the value.

**Why not a plain hash:** Pakistani mobile numbers and CNICs come from small, predictable spaces (roughly 10^10 mobile numbers). An attacker can hash every candidate and compare digests, which reverses a plain SHA-256 almost instantly. A secret key prevents this only for people who do not have the key.

**Key handling:**
- Whoever holds the key can run the same brute force. The key must be protected like the original data, kept out of version control, and rotated if it is exposed.
- Rotating the key breaks linkage with earlier pseudonyms. That is intended.

### 7.3 Pseudonym mapping tables
If a reversible mapping (pseudonym → original) is ever kept, it is as sensitive as the original data. It must be stored separately from the pseudonymised output, with restricted access, and it must never be shared with consumers of that output. This prototype does not create a mapping table.

### 7.4 No technique guarantees anonymity
Anonymity is a property of a released dataset relative to what an adversary knows. It is not a property of one transformation. Output can remain re-identifiable in three ways:

- through combined quasi-identifiers
- by joining with auxiliary data
- through detection misses: in the final run, 308 planted occurrences were not fully redacted (see `residual_pii_report.csv`)

---

## 8. Incident response

This applies when a possible exposure is found: real data in the repository, residual PII in a shared redacted file, or raw values in a log.

1. **Identify.** Record what was found, where, and when, using record ids and file names, not the values. Confirm that it is a real exposure.
2. **Contain / suspend.** Stop processing and distribution for the affected document set. Withdraw or quarantine affected outputs and copies.
3. **Preserve non-sensitive diagnostics.** Keep record ids, entity types, counts, the commit or config version and the log lines without values. Treat the affected documents themselves as sensitive.
4. **Notify the privacy/security owner** without delay. Any legal notification duties are assessed by them with qualified counsel. This prototype makes no legal determination.
5. **Root cause.** Find out why it happened, for example a missed format, a span error, a guard bypass or a log statement.
6. **Fix and add a regression test.** Fix the cause and add a test that fails without the fix, as was done for the dangerous misses in `tests/test_regression.py`. Re-run the evaluation and the residual check.
7. **Close with documentation.** Record the closure and lessons learned in `CHANGELOG.md`, and in `docs/DANGEROUS_MISSES.md` if a detection gap was involved.

---

## 9. Human review and limitations

Automated detection is fallible. The measured gaps in the final run were:

- PERSON recall of 0.7591
- lower-case names (0.1395) and ALL-CAPS names (0.1087)
- unlabelled 13-digit CNICs
- landmark-style addresses (0.0000)

Two checks run after redaction:

- **Value check:** `redactor.find_residuals` searches the redacted text for each planted value, using whole-value and digit-sequence matching.
- **Coverage check:** the evaluation counts planted occurrences that were not fully covered.

Both checks only work for **planted** synthetic values. They cannot find PII that nobody annotated. Any output intended for external sharing, public analytics or AI training needs human review first. `docs/DANGEROUS_MISSES.md` lists the failure modes to look for.

---

## 10. Governance

This project is an educational prototype. It does not:

- constitute or certify compliance with any privacy law
- replace a privacy impact assessment
- establish a data-processing agreement
- guarantee zero residual PII or anonymity

Before any use with real personal data, the following would be needed:

1. legal review
2. a formal privacy impact assessment
3. sign-off by a data-protection officer or equivalent
4. production hardening (authentication, audit logging, encryption at rest)
5. staff training on the pipeline's limits
6. a fresh evaluation on representative, properly governed data
