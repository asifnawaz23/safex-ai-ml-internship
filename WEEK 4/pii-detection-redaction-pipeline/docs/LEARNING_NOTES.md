# Learning Notes

These notes explain the concepts behind the project. They describe what the code does; they do not claim what the author has studied or understood. The two sections near the end are for the author to fill in personally.

## Five-line learning plan (Phase 1)

1. Learn what Presidio's `AnalyzerEngine` and `AnonymizerEngine` each do, and how a `PatternRecognizer` with context words is registered.
2. Learn how exact-span TP/FN/FP matching turns into precision, recall and F1.
3. Write and test regex patterns with boundaries for Pakistani mobile and CNIC formats, including negative cases.
4. Compare default Presidio against the improved pipeline on the same seeded dataset and explain every regression.
5. **Measurable target:** without notes, explain exact-span recall and reproduce the improved CNIC recall from `output/metrics/improved_metrics.csv` by hand as TP/(TP+FN) = 195/(195+8) = 0.9606. Also name the root cause of the 8 remaining CNIC misses.

## What Presidio does

Presidio is a Microsoft open-source SDK for finding and de-identifying PII in text.

- **`presidio-analyzer`** finds candidate spans.
  - A `RecognizerRegistry` holds recognisers: regex-based `PatternRecognizer`s, the spaCy-backed `SpacyRecognizer`, and others such as `PhoneRecognizer`, which uses python-phonenumbers.
  - Each recogniser returns `RecognizerResult(entity_type, start, end, score)`.
  - A context enhancer raises the score when context words appear near a match.
  - A `score_threshold` (0.35 here) drops weak results.
- **`presidio-anonymizer`** transforms the text, given those spans. This project uses the `replace` operator, so a phone becomes `[PHONE]`. A `conflict_resolution` strategy decides what happens when spans overlap.

The analyzer never changes the text, and the anonymizer never detects anything. That is why the evaluation can score detection separately from redaction.

## Why ground truth is needed

Without known answers, you can only count what the detector found, never what it missed. The generator records every planted value with its exact offsets when it builds the document. Because those offsets are not derived from detector output, the evaluation is not circular.

## Recall vs precision

- **Recall** = TP/(TP+FN): of all real PII, how much was caught.
- **Precision** = TP/(TP+FP): of everything flagged, how much was really PII.

For redaction, low recall means PII leaks out, and that is the costly failure. Low precision means over-redaction: data is less useful and someone is annoyed, but nobody's CNIC is exposed. That is why the scope prioritises recall for direct identifiers, while still setting precision targets so the system cannot "win" by redacting everything.

**Why one miss is costly.** A single missed CNIC or phone number in a shared file is a full disclosure for that person. In the baseline, 202 of 203 CNICs survived redaction as whole values (`residual_pii_report.csv`).

## Why local formats need testing

Default Presidio 2.2.364 has no CNIC recogniser, and its `PhoneRecognizer` checks a fixed list of regions that does not include Pakistan. It still caught many `+92` and `03XX` numbers (baseline phone recall 0.9234), but it missed some. It also flags non-phone digit runs such as `1234567890`. Behaviour like this is only visible when you test local formats explicitly.

## Regex boundaries and context

- **Boundaries.** A pattern like `\d{5}` matches inside a CNIC, an invoice number or `UBW-12345`. The project uses lookarounds such as `(?<![\w+\-./])` and `(?![\w\-]|\.\d)`, so a match cannot start or end inside a longer token.
- **Context.** A plain 13-digit number is ambiguous (CNIC or barcode). It therefore scores 0.30, below the threshold. Only a context word such as "CNIC" or "identity" in the 5 words before it lifts the score above 0.35.
- **Tokenisation.** Context is matched on spaCy tokens. `NIC:4210112345671` is one token, so the context enhancer never sees the label. A label-anchored lookbehind pattern fixes this (DM-001).

## What changed from baseline to improved

| Change | Applies to | Effect (final run) |
|---|---|---|
| Six custom recognisers (phone, CNIC, customer id, postal code, address, labelled person) | improved | CNIC recall 0.0000 → 0.9606, ADDRESS 0.0000 → 0.8942, POSTAL_CODE and CUSTOMER_ID 0.0000 → 1.0000 |
| Span hygiene (`key=` prefix, labels, field delimiters) | both | baseline EMAIL recall 0.8886 → 1.0000 between the initial and final runs |
| Custom-over-built-in span precedence | both | fixed the phone span mismatch in DM-006 |
| Company-code allow-list | improved | FP-trap hits 193 → 9, but only for the generator's code formats |

Overall recall went from 0.5023 to 0.9071 and precision from 0.6190 to 0.8442.

## Remaining limitations

These are covered in [LIMITATIONS.md](LIMITATIONS.md):

- names in lower case, ALL CAPS or unlabelled prose
- landmark addresses
- unlabelled 13-digit CNICs
- optimistic, in-sample scores
- synthetic data only
- the small spaCy model

---

## AI suggestions I personally verified

*(Author to fill in. For each item: the suggestion, how you checked it, for example the command you ran or the file you read, and the result.)*

1.
2.
3.

## Suggestions I rejected or corrected, and why

*(Author to fill in with your own decisions.)*

1.
2.

**Agent-side corrections made during development.** These are recorded in `CHANGELOG.md`. They were found and fixed by the AI coding agent, not by the author, and are listed only as candidates the author may want to verify:

- An `AnalyzerEngine` built without an explicit NLP engine silently loads and downloads `en_core_web_lg` (D1).
- A bare `\d{5}` postal-code pattern matched invoice numbers, customer-id digits and CNIC blocks (D2).
- An NLP config without `ner_model_configuration` kept the CARDINAL and MONEY labels (D3).
- Offsets located with `text.find()` only find the first occurrence; they were replaced by construction-time offsets (D4).
- A plain 13-digit CNIC pattern at 0.6 turned barcodes into CNICs (D5).
- A salted SHA-256 "pseudonym" with a hard-coded salt was replaced by HMAC-SHA256 with a key from the environment.
- Several tests only asserted `isinstance(result, list)`; they were replaced with real assertions.
- Presidio's email recogniser could make an online `tldextract` lookup; it was forced onto the offline snapshot.

## Verification checklist for the author

- [ ] Run `.\.venv\Scripts\python.exe -m pytest -q` and confirm the pass/xfail counts in `docs/TESTING_AND_VALIDATION.md`.
- [ ] Run `python -m pii_pipeline.cli all` and confirm that `output/metrics/comparison.csv` matches the README table.
- [ ] Recompute one recall and one precision value by hand from `improved_metrics.csv`.
- [ ] Open `src/pii_pipeline/recognizers.py` and explain why `cnic_plain_13` scores 0.30.
- [ ] Try one phone format of your own with `redact --text ... --dry-run` and record the result.
- [ ] Read one row of `output/metrics/dangerous_misses.csv` and run its regression test: `pytest tests/test_regression.py::<name>`.
