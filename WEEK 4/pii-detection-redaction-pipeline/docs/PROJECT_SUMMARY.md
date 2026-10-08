# Project Summary

**PII Detection & Redaction Pipeline with Measured Recall and a Privacy Policy for an Urban Bottled Water Company.** This is an individual Week 4 project by Member 5. The company is fictional.

**Problem.** Company documents such as orders, delivery notes, contact forms, subscriptions, support messages and internal notes contain personal data. That data must be removed before the documents are used for analytics, testing or AI processing, and the removal has to be measured rather than assumed.

**Why Presidio.** Microsoft Presidio is open source and runs locally. It separates detection (`AnalyzerEngine`) from transformation (`AnonymizerEngine`), and it can be extended with custom recognisers. It runs on a CPU-only 8 GB laptop with the small spaCy model `en_core_web_sm` 3.8.0.

**Data and ground truth.** A seeded generator (seed 42) produces 870 synthetic records: 850 planted records plus 20 challenge records, across 6 document types. They contain 3412 planted occurrences of 7 entity types and 1038 annotated false-positive traps. Offsets are recorded while each document is built, and they are validated afterwards. The ground truth never comes from detector output.

**Custom recognisers.**

- Pakistani mobile phones in 03XX, +92 and 0092 forms
- CNICs: hyphenated, spaced, labelled plain, and unlabelled plain (unlabelled ones need context)
- `UBW-` customer ids
- labelled or city-suffixed postal codes
- dwelling-anchored addresses
- labelled person names

Shared post-processing maps labels and cleans span boundaries. The improved mode also uses a company-code allow-list.

**Evaluation method.** Each predicted span is matched one-to-one against the ground truth, and only exact spans count as hits. Precision, recall and F1 are reported per type. The secondary measures are:

- overlap recall
- redaction coverage
- FP-trap hit rate
- residual planted values in the redacted text
- occurrences that were not fully redacted

**Results** (`output/metrics/comparison.csv`, final run):

| | Recall | Precision | F1 |
|---|---|---|---|
| Baseline (default Presidio) | 0.5023 | 0.6190 | 0.5546 |
| Improved | 0.9071 | 0.8442 | 0.8745 |

Recall by entity type:

| Entity | Baseline | Improved |
|---|---|---|
| CNIC | 0.0000 | 0.9606 |
| PHONE_NUMBER | 0.9234 | 1.0000 |
| ADDRESS | 0.0000 | 0.8942 |
| PERSON | 0.6291 | 0.7591 |
| EMAIL_ADDRESS, POSTAL_CODE, CUSTOMER_ID (improved) | | 1.0000 each |

Redaction results:

| | Baseline | Improved |
|---|---|---|
| Residual planted values | 1244 | 236 |
| Residual direct-identifier rate | 0.1962 | 0.0063 |
| Occurrences not fully redacted | | 308 |
| FP-trap hit rate | 0.1859 | 0.0087 |

The improved FP-trap rate is optimistic because of the allow-list. Every pre-registered target is met in the final run, but these are in-sample results.

**Misses and fixes.** Fifteen actual misses from the first run were reviewed. Ten were fixed, each with a regression test:

- CNIC label glued to the number
- spaced CNICs
- dot-separated and 4-3-4 phones
- custom span precedence
- `email=` prefix
- PERSON span boundaries

Five are documented as not fixed by design: unlabelled CNICs (a trade-off against barcodes) and four name forms the small model misses. These five have a trade-off test and four strict xfail tests.

**Privacy decisions.**

- All processing is local, and tldextract is forced offline.
- A synthetic-only guard is in place.
- Logs never contain raw text, and a masking filter adds a second line of defence.
- Originals and redacted output are kept in separate trees.
- Pseudonyms use HMAC-SHA256 with an environment key instead of plain hashes.
- Incident response has seven steps.

The policy is a prototype, not a compliance claim.

**Tests.** 197 tests were collected. The run gave 193 passed, 0 failed, 0 skipped and 4 xfailed (strict).

**Limitations.**

- The scores are optimistic and in-sample. On held-out formats, recall is 0.5784.
- Data is synthetic only.
- Weak cases remain: lower-case, ALL-CAPS and unlabelled names, and landmark addresses (recall 0.0000).
- The model is small.
- There is no guarantee of zero residual PII.

**Next steps.**

- Real classmate peer review (PENDING)
- Video walkthrough (PENDING)
- A stronger NER model, if the hardware allows
- A reviewer flag for unlabelled 13-digit numbers
- Evaluation on a held-out generator or a governed real-style corpus
