# Limitations

The numbers come from `output/metrics/` (final run) unless stated otherwise.

## Evaluation validity
- **The scores are optimistic.** The custom recognisers, span hygiene and allow-list were written by someone who knew the generator's formats. The dangerous-miss fixes were found by inspecting this same dataset, so the final numbers are in-sample and not a held-out estimate. A fairer signal is the `heldout_format` tag, which covers formats the recognisers were not first written for: improved recall there is 0.5784, against 0.9071 overall.
- **The FP-trap rate is optimistic.** The improved rate of 0.0087 (9/1038) depends on an allow-list that matches the generator's own `ORD-`, `BATCH-` and vehicle-plate formats. Those three trap kinds account for 184 of the 193 baseline hits. The kinds the allow-list does not cover hit the same in both modes: date 4/159 and order_digits 5/120. Code formats outside the list are not covered.
- **Synthetic data only.** Real documents bring other phrasing, OCR noise, typos, mixed Urdu/English, Roman Urdu and formats this generator does not produce. No real data was used, by design.
- **Single seed and dataset.** All results come from seed 42 and 870 records. No variance across seeds was measured.
- **Exact-span scoring is strict.** Boundary disagreements count as both FN and FP even when the value was redacted. Overlap recall and redaction coverage are reported next to it for that reason.

## Detection gaps (improved pipeline, final run)
- **Names.** PERSON recall is 0.7591 and precision 0.6403. Some name forms are mostly missed:
  - lower-case names: 0.1395
  - ALL-CAPS names: 0.1087
  - unlabelled names in prose and staff signatures (DM-009 to DM-012, strict xfail tests)

  On the false-positive side, spaCy tags some locality and city tokens as PERSON. In a manual CLI probe during the docs step, it also tagged the word "Barcode" at the start of a sentence as PERSON. That probe was a single example, not a measured rate.
- **Landmark addresses.** These ("near X mosque, behind Y market") are not targeted: recall is 0.0000 on 43 occurrences. 44 addresses were not fully redacted, and 38 of them are partial leaks that the whole-value residual check does not report.
- **Unlabelled 13-digit CNICs.** These stay below the threshold on purpose, to avoid redacting barcodes. All 8 remaining CNIC misses are plain, no-context numbers.
- **Context window.** Presidio's context enhancer only looks at the 5 words before an entity (`context_prefix_count=5`, no suffix). A label that follows the number, or one glued to it as a single token, does not help unless a pattern anchors it explicitly.
- **Built-in phone false positives.** Presidio's `PhoneRecognizer` flags a plain `1234567890` (score 0.4). This is kept, because the built-in recogniser stays enabled in both modes.
- **Format candidates, not validity.** The phone and CNIC patterns detect format candidates. They cannot tell whether a number is real or assigned.

## Model and environment
- **Small model.** `en_core_web_sm` is weaker than Presidio's default `en_core_web_lg`. It was chosen for the 8 GB RAM and limited-disk constraint. Larger and Transformer models were not evaluated.
- **Platform.** English pipeline only. Tested only on Windows 11 with Python 3.13.5.
- **Runtime.** Runtime depends on machine load. Four runs (three consecutive review runs plus the final-audit run) gave baseline 10.8–15.5 s and improved 12.1–12.8 s. An earlier run recorded 735.7 s for baseline during a transient slowdown.

## Privacy and security
- **No residual guarantee.** The pipeline does not guarantee zero residual PII. In the final run, 308 planted occurrences in improved mode were not fully redacted. Separately, the value check still found 236 planted values verbatim in the redacted text.
- **Residual checks cover planted values only.** PII that nobody annotated cannot be measured.
- **The synthetic-only guard is a tripwire.** It checks email domains and a `synthetic` column; it cannot prove that text is synthetic.
- **No access control.** The prototype has no authentication, audit logging or encryption at rest.
- **HMAC key handling.** Keyed pseudonyms are only as safe as the key, and anyone holding the key can brute-force predictable identifiers.
- **Not a compliance tool.** The privacy policy is a proposed prototype policy, not a legal compliance statement.

## Process
- **Peer review:** PENDING.
- **Video walkthrough:** PENDING.
- **Screenshots:** PENDING.
- **Git:** versioned in the parent repository `asifnawaz23/safex-ai-ml-internship` under `WEEK 4/pii-detection-redaction-pipeline`. There is no CI; all test results are from local runs.
