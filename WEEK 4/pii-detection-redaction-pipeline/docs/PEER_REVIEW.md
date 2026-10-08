# Peer Review Record

> **Status: PENDING.** No peer review has been conducted yet.
>
> This file is a template. A real classmate must do the review, and the author fills in the record below afterwards. Do not invent reviewer names, dates, feedback or approval. Record the reviewer's name only with their permission; otherwise use an identifier such as "Reviewer A".

## Instructions for the reviewer

Your job is to find gaps: missed PII, false alarms and confusing parts. Approving the project is not the goal. Use **synthetic values only**. Never type a real phone number, CNIC or email address. The tool refuses email domains other than `example.com`, `example.org` and `example.net`.

### Setup (Windows PowerShell, from the repository root)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"
& $py -m pii_pipeline.cli all        # dataset, both experiments, metrics, charts
```

Use `redact --text "..." --dry-run` for a masked list of detections, or leave out `--dry-run` to see the redacted text.

### Checklist

| # | Task | Suggested starting point | What to record |
|---|---|---|---|
| 1 | **Try a phone format you think might be missed** | `& $py -m pii_pipeline.cli redact --text "Rider number 0321/1234567, please call"`. Invent your own variants with different separators, brackets, a `+92` prefix or extra spaces. | The formats you tried and which were detected |
| 2 | **Embed a CNIC in ordinary text** | `& $py -m pii_pipeline.cli redact --text "He said his card is 4210112345671 and left"`. Also try a CNIC with hyphens or spaces, and one with and without a label word. | Whether it was detected, and with which label |
| 3 | **Find an ambiguous number that should NOT be flagged** | `& $py -m pii_pipeline.cli redact --text "Barcode 8964000123456, invoice 54321, 12 x 19L bottles" --dry-run` | Any false detections |
| 4 | **Is the redacted output understandable?** | `& $py -m pii_pipeline.cli redact --record-id REC-00008`, or open `output/redacted/improved_redacted.jsonl` | Whether the meaning survives and the placeholders are clear |
| 5 | **Name one confusing part of the README or CLI** | Follow `README.md` from scratch | The part that confused you |

Optional: run `& $py -m pytest -q` and note the result.

---

## Review record (fill in after the real review)

| Field | Value |
|---|---|
| Date | PENDING |
| Reviewer identifier (with permission) | PENDING |
| Method (in person / screen share) | PENDING |
| Time spent | PENDING |

### Tests attempted

| # | Tried? | Input used (synthetic) | What happened | Issue? |
|---|---|---|---|---|
| 1 Phone format | | | | |
| 2 CNIC in text | | | | |
| 3 Ambiguous number | | | | |
| 4 Redacted output | | | | |
| 5 README/CLI clarity | | | | |

### Feedback (reviewer's own words)

PENDING

### Issues discovered

PENDING

### Changes made because of the feedback

PENDING

### Regression tests added

PENDING. Add one test in `tests/test_regression.py` per fixed issue and name it here.

### Remaining issues

PENDING

### Sign-off

- [ ] The author confirms that the feedback has been incorporated or documented.
- [ ] The reviewer confirms that this record reflects their testing.
