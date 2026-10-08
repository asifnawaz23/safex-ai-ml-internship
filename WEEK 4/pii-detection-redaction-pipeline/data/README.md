# Data

Everything in `data/generated/` is **synthetic**. It is produced by `src/pii_pipeline/synthetic_data.py` with a fixed seed and contains no real personal information. Names come from fixed fictional lists, phone and CNIC digits are random, and email addresses use only the reserved domains `example.com`, `example.org` and `example.net`.

Regenerate (from the repository root, PowerShell):

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe -m pii_pipeline.cli generate --seed 42 --count 850
```

The same seed and count always produce byte-identical files; the SHA-256 of each file is recorded in `dataset_manifest.json`.

## Files

| File | Content |
|---|---|
| `synthetic_documents.csv` | One row per document: `record_id, doc_type, source, synthetic, text` |
| `ground_truth.json` | Every planted PII occurrence (schema below) |
| `ground_truth.csv` | Same annotations as CSV (`tags` joined with `;`) |
| `fp_traps.json` | Annotated false-positive traps: non-PII strings that look like PII |
| `dataset_manifest.json` | Seed, counts per entity/document type/trap kind, generator version, file hashes |

`source` is `planted` for the 850 generated records (`REC-00001` …) and `challenge` for the 20 hand-designed hard cases (`CHAL-001` …). `synthetic` is always `true`; the pipeline refuses a documents file without it.

## Ground-truth schema

| Field | Meaning |
|---|---|
| `annotation_id` | `<record_id>-E<nn>` |
| `record_id`, `doc_type` | Document the occurrence belongs to |
| `entity_type` | `PERSON`, `PHONE_NUMBER`, `CNIC`, `EMAIL_ADDRESS`, `ADDRESS`, `POSTAL_CODE`, `CUSTOMER_ID` |
| `text` | Exact planted substring |
| `start`, `end` | Character offsets, **0-based, end-exclusive**: `text == document[start:end]` |
| `source` | `planted` or `challenge` |
| `expected_handling` | `REDACT` |
| `tags` | Edge-case tags, e.g. `phone_local_space`, `cnic_plain`, `no_context`, `lowercase_name`, `heldout_format`, `nested`, `repeated_value`, `unicode_context` |

Trap schema: `trap_id, record_id, doc_type, kind, text, start, end, expected_handling (KEEP), tags`. Kinds: order numbers (`order_number`), order digit runs (`order_digits`), invoice totals, bottle counts, dates, batch codes, 13-digit barcodes, 11-digit tracking numbers, 5-digit invoice numbers and vehicle plates.

## Current contents (seed 42, count 850; from `dataset_manifest.json`)

| | Count |
|---|---|
| Records | 870: 850 planted and 20 challenge. 23 of them contain no PII. |
| Annotations | 3412 |
| By entity type | PERSON 1100, PHONE_NUMBER 640, CUSTOMER_ID 445, EMAIL_ADDRESS 431, ADDRESS 416, CNIC 203, POSTAL_CODE 177 |
| By document type | contact_form 146, customer_service_message 146, delivery_note 145, delivery_order 145, internal_operational_note 145, subscription_record 143 |
| FP traps | 1038: bottle_count 305, date 159, vehicle_plate 124, order_digits 120, batch_code 89, invoice_total 72, invoice_number 67, order_number 58, barcode 22, tracking_number 22 |

## How the ground truth stays independent

Documents are assembled segment by segment. When a value is appended, its start offset is the current text length, so offsets are known by construction. Nothing is searched for in the finished text and no detector output is used. After assembly every annotation and trap is re-checked against the text (`ground_truth.validate_annotations`), and traps are checked never to overlap a PII span.

Values tagged `heldout_format` (dot-separated and 4-3-4 phones, space-separated CNICs, landmark addresses) use formats the custom recognisers were not originally written for. They exist to measure generalisation.

## Safe to commit

All files in `data/generated/` are synthetic and safe to commit. Never place real records in this repository; `data/raw/`, `data/real/` and `data/private/` are git-ignored as a safety net.
