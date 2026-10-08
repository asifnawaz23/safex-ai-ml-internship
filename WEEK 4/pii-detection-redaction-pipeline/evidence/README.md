# Evidence checklist

**Status: PENDING (user action).** Capture the screenshots yourself on your own machine and save them in `evidence/screenshots/`. None are included yet, and nothing here is simulated. Only `.gitkeep` is in that folder.

Before capturing, open PowerShell in the repository root and run once:

```powershell
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"
```

All values on screen are synthetic. Still, make sure no other window, real email, token or personal file is visible.

| # | Screenshot | File name | Command / what to show |
|---|---|---|---|
| 1 | Project structure | `01_structure.png` | `tree /F config src scripts tests docs evidence` (or the Explorer view of the repository root) |
| 2 | Environment and versions | `02_environment.png` | `& $py --version; & $py -m pip freeze \| Select-String "presidio\|spacy\|en.core\|pandas\|matplotlib\|pytest"` |
| 3 | Dataset generation output | `03_generate.png` | `& $py -m pii_pipeline.cli generate` (expect 870 records, 3412 annotations, 7 entity types, "All offsets valid: True") |
| 4 | Sample ground-truth record | `04_ground_truth.png` | `Import-Csv data\generated\ground_truth.csv \| Where-Object record_id -eq 'REC-00001' \| Format-Table annotation_id,entity_type,start,end,tags -AutoSize` |
| 5 | Baseline run | `05_baseline.png` | `& $py -m pii_pipeline.cli baseline` |
| 6 | Improved run | `06_improved.png` | `& $py -m pii_pipeline.cli improved` |
| 7 | Redacted output | `07_redacted.png` | `& $py -m pii_pipeline.cli redact --record-id REC-00008` |
| 8 | Per-type metrics | `08_metrics.png` | `Import-Csv output\metrics\comparison.csv \| Format-Table entity_type,gt_count,baseline_recall,baseline_precision,improved_recall,improved_precision,improved_f1 -AutoSize` (widen the window) |
| 9 | Charts | `09_charts.png` | Open `output\charts\recall_by_entity.png` and `output\charts\precision_recall_comparison.png` |
| 10 | Test results | `10_tests.png` | `& $py -m pytest -q -rx` (expect 193 passed, 4 xfailed) |
| 11 | Dangerous-miss report | `11_dangerous_misses.png` | `Import-Csv output\metrics\dangerous_misses.csv \| Format-Table case_id,entity_type,category_before,category_after,verification_status -AutoSize` |
| 12 | Peer-review changes | `12_peer_review.png` | Take this only **after** the real review: `docs/PEER_REVIEW.md` filled in, plus the regression test added for it (`& $py -m pytest tests/test_regression.py -q`) |
| 13 | Final CLI demo | `13_cli_demo.png` | `& $py -m pii_pipeline.cli redact --text "Call 0321-1234567 or mail a.b12@example.org" --dry-run`, then the same command without `--dry-run` |

If a number on your screen differs from the docs (for example after you regenerate), the CSVs are the source of truth. Update the docs; do not edit the screenshot.
