# Changelog

All dates 2026-10. Every entry lists the reason and how it was verified. Numbers come from `output/metrics/` (initial run: `output/metrics/initial/`).

## [1.0.0] — 2026-10-06

### Scope
- `docs/SCOPE_STATEMENT.md`: business context, direct vs contextual identifiers (Direct: PERSON, PHONE_NUMBER, CNIC, EMAIL_ADDRESS, ADDRESS; contextual: POSTAL_CODE, CUSTOMER_ID), out-of-scope list, users.
- Initial recall targets kept unchanged. Precision, overall-recall, FP-trap-rate and residual targets added **before any dataset-level evaluation was run**, because the original list had recall only. Logged in the scope statement's target history.

### Dependencies
- Pinned exactly what was installed and verified: presidio-analyzer/anonymizer 2.2.364, spacy 3.8.16, pandas 2.3.3, matplotlib 3.11.2, pytest 8.4.2.
- spaCy model: **en_core_web_sm 3.8.0** (12.8 MB wheel, pinned by URL + sha256). Presidio's default config uses en_core_web_lg (~500 MB), which does not fit the disk/RAM budget. Verified: `spacy.util.is_package('en_core_web_lg')` is False.
- Removed pytest-cov from requirements (not used).
- Verified with `pip install -r requirements.txt --dry-run`: no new packages to install.

### Synthetic data generator (rewritten)
- Reason: the prototype had one template per document type and located values with `text.find()` (first occurrence only).
- Now: segment builder records offsets at append time; ≥3 phrasing variants per document type, shuffled field order, optional fields, label/case/spacing variation, Urdu context, 11 phone formats, 3 CNIC formats, 8 address formats, held-out formats, nested and repeated values, 20 challenge records, 1038 annotated FP traps.
- Verified: 870 unique records, 3412 annotations, 7 entity types, all offsets valid; two runs give identical SHA-256 hashes (`tests/test_synthetic_data.py`).

### Baseline (Experiment A)
- Real `AnalyzerEngine` with `load_predefined_recognizers(languages=["en"])` and en_core_web_sm, entities PERSON/PHONE_NUMBER/EMAIL_ADDRESS/LOCATION, threshold 0.35. Verified in the installed package: no default recogniser for CNIC, Pakistani postal codes or customer IDs.

### Custom recognisers (Experiment B)
- PakistaniPhoneRecognizer, PakistaniCNICRecognizer, UBWCustomerIDRecognizer, PakistaniPostalCodeRecognizer, PakistaniAddressRecognizer, LabelledPersonRecognizer. Label mapping `LOCATION -> ADDRESS` in `config/settings.json`.

### Evaluation
- Deterministic one-to-one matching: exact > wrong label > partial (best IoU) > duplicate/spurious > missed. Exact span is primary; overlap recall and redaction coverage are secondary. N/A on zero denominators. FP-trap hit rate over the annotated traps.

### Bugs found in the prototype (with regression tests in `tests/test_regression.py`)
- D1: AnalyzerEngine built without an explicit NLP engine silently loads/downloads en_core_web_lg. Fix: `build_nlp_engine()` loads Presidio's `default.yaml`, overrides the model name, raises if the model is missing. Test `test_d1_...`.
- D2: postal pattern `\d{5}` matched invoice numbers, UBW-12345 digits and CNIC blocks. Fix: labelled and city-suffixed patterns only. Test `test_d2_...`.
- D3: NLP config without `ner_model_configuration` kept CARDINAL/MONEY labels. Fix: keep Presidio's NER config. Test `test_d3_...`.
- D4: `find()`-based offsets. Fix: construction-time offsets. Test `test_d4_...`.
- D5: plain 13-digit CNIC pattern scored 0.6, so barcodes became CNICs. Fix: 0.3 + context. Test `test_d5_...`.
- Evaluation dict keyed by span silently dropped duplicate predictions; dead alias code. Rewritten.
- Salted SHA-256 with a hard-coded default salt. Replaced by HMAC-SHA256 with a key from `PII_PIPELINE_HMAC_KEY`.
- Several tests asserted only `isinstance(result, list)`. Replaced with real assertions.
- Presidio's EmailRecognizer uses tldextract, whose default extractor may fetch the public-suffix list online. Fix: offline extractor using the bundled snapshot. Test `test_analysis_makes_no_network_connections`.

### Dangerous-miss fixes (after the first full run)
Initial improved run: recall 0.8664, precision 0.7624, 456 FNs, FP-trap hit rate 0.1917. 15 actual misses reviewed (`output/metrics/dangerous_misses.csv`).
- CNIC label glued to number (`NIC:<digits>`, one spaCy token): label-anchored pattern. `test_dm_cnic_label_glued_to_number`.
- Space-separated CNIC: new pattern. `test_dm_cnic_space_separated`.
- Dot-separated and 4-3-4 phones: separator/grouping patterns. `test_dm_phone_dot_separated`, `test_dm_phone_4_3_4`.
- Built-in phone span `(0321-...` overriding the exact custom span: custom recogniser precedence in same-label containment. `test_dm_phone_custom_span_precedence`.
- `email=` swallowed by Presidio's email regex in key=value text; spaCy PERSON spans crossing `|`, `(`, line breaks, or including labels: span hygiene in the shared normalisation. **Applied to both modes**, so baseline numbers also changed (baseline EMAIL recall 0.8886 → 1.0000, PERSON 0.5655 → 0.6291). Tests `test_dm_email_field_key_prefix_trimmed`, `test_dm_person_span_cut_at_field_delimiter`, `test_dm_person_leading_label_trimmed`.
- FP traps (batch codes and vehicle plates tagged PERSON, ORD- digits tagged PHONE_NUMBER): company-code allow-list in improved mode only. `test_fp_company_codes_not_redacted`.
- Not fixed by design: plain CNIC without context (barcode trade-off, `test_dm_cnic_plain_no_context_documented_tradeoff`), lower-case/ALL-CAPS/unlabelled names (model limit).
- Final improved run: recall 0.9071, precision 0.8442, 317 FNs, FP-trap hit rate 0.0087; 10 of 15 cases DETECTED_AFTER_FIX, 5 NOT_FIXED_BY_DESIGN.
- No generator changes were made after the first evaluation.

### Privacy and security
- Path validation, synthetic-only guard (email domains, `synthetic` column), log filter masking PII-like strings, keyed pseudonyms, separate output trees, dry-run preview, CLI exit code 2 on refusals. Verified in `tests/test_privacy.py`; a scan of `output/pipeline.log` found 0 planted values.

### Final verification
- `python -m pytest -q`: 191 passed. `python -m pii_pipeline.cli all` exit 0. A second run produced byte-identical metric CSVs, except the runtime-bearing `experiment_summary.csv`, `summary.json` and `*_engine.json`.

## [1.0.1] — 2026-10-07 (review fixes)

- Runtime: the 1.0.0 artifacts recorded baseline 735.7 s, which came from a transient machine slowdown, while the README claimed about 11–12 s. Re-ran `all` three times; the final artifacts record baseline 11.687 s / improved 12.672 s. README now copies these numbers from `experiment_summary.csv` and mentions the earlier outlier.
- Reproducibility claim corrected: README now lists the files that are byte-identical across runs and the four runtime-bearing files that are not. Verified by hashing every file under `data/generated` and `output/` after two consecutive `all` runs.
- Residual report: `residual_pii_report.csv` gained `not_fully_redacted` and `partial_leaks_not_value_matched` columns. Reason: whole-value matching missed partly surviving addresses and names. The new columns come from `EvaluationReport.uncovered_ids`, computed on original-text offsets. The residual definition is unchanged. Improved: 308 not fully redacted, 78 of them partial leaks. Test: `test_partial_leak_counted_next_to_value_residuals`.
- Dangerous misses DM-009 to DM-012 (not fixed by design) now have strict `xfail` tests that document the miss. If behaviour changes, the XPASS fails the suite. `dangerous_misses.csv` names the tests.
- Test isolation: the tests used to write to the real `output/pipeline.log`. A session fixture in `tests/conftest.py` now redirects `logging.log_file` to a temp file. Test: `test_test_runs_do_not_write_to_repo_log_file`. The old log, which mixed test and CLI lines, was deleted and regenerated by a CLI run. It has 15 lines, contains 0 of 3176 planted values (≥5 chars), and has no test lines.
- README discloses that the improved FP-trap rate depends on the company-code allow-list, with the per-kind split.
- `python -m pytest -q`: 193 passed, 4 xfailed.

## [1.0.2] — 2026-10 (documentation set)

Documentation only. No source, test, data or metric file changed.

- **New documents.** `docs/EVALUATION_REPORT.md`, `DANGEROUS_MISSES.md`, `PROJECT_SUMMARY.md`, `TESTING_AND_VALIDATION.md`, `LIMITATIONS.md`, `LEARNING_NOTES.md` and `VIDEO_WALKTHROUGH.md`.
  - Reason: brief sections 9, 11, 14, 16, 18 and 20.
  - Verification: every table was copied from `output/metrics/*.csv`, `summary.json` and `*_engine.json`, then re-read against the CSVs after writing.
  - Document-level counts (records fully matched or fully covered) were computed directly from `per_document_metrics.csv`.
- **README rewritten** to cover every section the brief requires, including the stack table with the pinned versions, the results table from `comparison.csv`, the embedded `recall_by_entity.png`, and GitHub instructions for the nested-repository situation.
  - Verification: the CLI commands shown were run during this step:
    - `redact --text` (exit 0)
    - `redact --text ... --dry-run` (exit 0)
    - `redact` with a non-`example.*` email (exit 2)
    - `redact --record-id REC-00008` (exit 0)
    - `scripts\run_baseline.py --help` without `PYTHONPATH` (exit 0)
- **Privacy policy v1.1.**
  - Section 7.2 now describes the implemented HMAC-SHA256 with an environment key. It previously described a salted SHA-256 that no longer exists.
  - It explains why plain hashes of phones and CNICs are guessable, and adds pseudonym-mapping protection (7.3).
  - Incident response was reordered into the brief's 7 steps: identify, contain, preserve diagnostics, notify, root cause, fix plus regression test, closure.
  - Logging now names the real safeguards (`RawTextRedactingFilter`, `mask_value`). It also states that `logging.log_raw_text` is read but not used to log raw text. Previously it named a non-existent `log_pii` switch.
  - The residual check now references `find_residuals` and the coverage count. It previously referenced a non-existent `verify_redaction()`.
  - Verification: the function names were checked with a search of `src/`.
- **Architecture** updated for `pipeline.py`, all 6 custom recognisers, normalisation, conflict handling and the offline guard. The claim "verified by design" was replaced by what the tests actually check.
- **Peer review template** now has the brief's 5 checklist items with working synthetic commands, which were run during this step. Every record field is PENDING.
- **Evidence checklist** now lists exact commands for all 13 screenshots. No screenshots were created.
- **Finding during the docs step (not fixed).** A manual dry run of "Barcode 8964000123456, invoice 54321, 12 x 19L bottles" showed spaCy tagging the word "Barcode" as PERSON. The 13-digit barcode itself was not flagged. This is recorded in `docs/LIMITATIONS.md` as a single observation, not a measured rate.
- **Tests re-run:** `python -m pytest -q -rxXs` gave 193 passed, 4 xfailed in 8.50 s. The SHA-256 of `output/pipeline.log` was unchanged by the run.

## [1.0.3] — 2026-10-07 (final audit)

- **Clean-state re-run.** Deleted every generated file under `data/generated/` and `output/` (except the irreproducible `output/metrics/initial/` snapshot), then ran `generate`, `baseline`, `improved`, `evaluate`, `reports` and `pytest -q`. All exited 0.
- **Reproducibility verified.** Against hashes taken before deletion, every regenerated file was byte-identical except the runtime-bearing `experiment_summary.csv`, `summary.json`, `baseline_engine.json`, `improved_engine.json` and `output/pipeline.log`. Re-running `scripts\generate_dataset.py`, `scripts\evaluate.py` and `scripts\build_reports.py` afterwards changed no file.
- **Docs fixed to match the CSVs.** Only the runtime differed: `experiment_summary.csv` now records baseline 10.787 s (12.4 ms/record) and improved 12.081 s (13.89 ms/record). README, `docs/EVALUATION_REPORT.md` and `docs/LIMITATIONS.md` updated. Every other metric in README, EVALUATION_REPORT and PROJECT_SUMMARY matched.
- **Tests:** `python -m pytest -q` gave 193 passed, 4 xfailed (197 collected), 0 failed, 0 skipped.

## [1.0.4] — 2026-10-07 (portfolio README and assets)

- **README rewritten** for the portfolio: hero banner (light and dark variants via `<picture>`), factual static badges (the tests badge says "local run"; there is no CI), an at-a-glance strip, a table of contents, a "How it works" walkthrough of REC-00008, engineering decisions, Week 1–4 navigation and an author section. Limitations, peer review, video and evidence screenshots stay visible and PENDING.
- **New script:** `scripts/render_readme_assets.py` generates `docs/assets/` from the committed CSVs and from real CLI output captured via subprocess (`docs/assets/captures/`). Assets: `pii-pipeline-hero.svg`, `pii-pipeline-hero-light.svg`, `recall_precision_3d.png` (matplotlib mplot3d), `redaction-before-after.svg` and `terminal-{generate,evaluate,redact,pytest}.svg`. The terminal images are renders of captured output, not screen captures.
- No change to `src/`, `tests/`, `config/`, `data/generated/` or the metrics. `baseline`/`improved` were not re-run, so the runtime figures are unchanged.
- **Verification:** `python -m pytest -q` gave 193 passed, 4 xfailed. Every SVG parses as XML and contains no `<script>` and no external resources. Every in-project image or link path in the README exists, and the four cross-week README links exist in git `HEAD`.
