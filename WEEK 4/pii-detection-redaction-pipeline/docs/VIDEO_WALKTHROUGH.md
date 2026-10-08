# Video Walkthrough Plan

**Status: PENDING.** You record this yourself. No video has been recorded, and none is linked anywhere in this repository.

- **Target length:** about 8 minutes (5–10 allowed).
- **Tools:** any free screen recorder, for example the Windows Snipping Tool screen recording or OBS Studio.
- **Before recording:**
  - Close every window that is not part of the project.
  - Hide email, chat and browser tabs that show anything personal.
  - Never type real personal data during the demo.
- **Shell setup** (repository root):

```powershell
$env:PYTHONPATH = "src"
$py = ".\.venv\Scripts\python.exe"
& $py -m pii_pipeline.cli all     # run once before recording so all outputs exist
```

## Timeline

| Time | Segment | On screen |
|---|---|---|
| 0:00–0:40 | Intro and problem | README title |
| 0:40–1:30 | Scope and synthetic safety | `docs/SCOPE_STATEMENT.md`, `data/README.md` |
| 1:30–2:20 | Architecture | Mermaid diagram in README or `docs/ARCHITECTURE.md` |
| 2:20–3:00 | Baseline run | `& $py -m pii_pipeline.cli baseline` |
| 3:00–4:00 | Custom PK phone and CNIC recognisers | `src/pii_pipeline/recognizers.py` |
| 4:00–4:40 | Example redaction | `redact --text ... --dry-run`, then without `--dry-run` |
| 4:40–5:40 | Baseline vs improved metrics | `output/metrics/comparison.csv`, `output/charts/recall_by_entity.png` |
| 5:40–6:30 | One real miss and its fix | `docs/DANGEROUS_MISSES.md` (DM-001), its regression test |
| 6:30–7:05 | Privacy policy | `docs/PRIVACY_POLICY.md` sections 6–8 |
| 7:05–7:35 | Tests | `& $py -m pytest -q` |
| 7:35–8:10 | Limitations, future work, close | `docs/LIMITATIONS.md` |

## Script (first person; adjust the wording so it sounds like you)

**0:00 Intro.** "Hi, I'm Member 5. This is my Week 4 project: a PII detection and redaction pipeline for a fictional company, the Urban Bottled Water Company. Their delivery orders, contact forms and support messages contain names, Pakistani phone numbers, CNICs, emails and addresses. Before those records go to analytics or AI tools, the personal data has to come out, and we need to know how reliably that happens."

**0:40 Scope and safety.** "I cover seven entity types:

- direct identifiers: names, phones, CNICs, emails and addresses
- contextual identifiers: postal codes and customer account ids

Everything here is synthetic. A seeded generator creates 870 records, which are 850 normal ones plus 20 hand-made challenge cases. It records 3412 planted PII occurrences with exact offsets as it builds each document. It also annotates 1038 false-positive traps, such as order numbers, barcodes and bottle counts. Emails use only example.com, .org and .net, and the tool refuses anything else."

**1:30 Architecture.** "Both experiments use Microsoft Presidio with the small spaCy model, en_core_web_sm. I chose it because of my 8 GB laptop. Presidio's default would pull the 500 MB large model, so the code refuses to download it. The steps are:

1. The analyzer finds spans.
2. A shared normalisation step maps labels and cleans up span boundaries.
3. The anonymizer replaces each span with a placeholder like [PHONE].
4. The evaluation compares the predictions against the ground truth with exact-span, one-to-one matching."

**2:20 Baseline.** "This is default Presidio. Overall recall is 0.5023 and precision 0.6190. The interesting part is what's missing: there is no default recogniser for CNICs, Pakistani postal codes or our customer ids, so their recall is zero. Its spaCy location spans never match a full street address either."

**3:00 Custom recognisers.** "So I added six custom recognisers. Here's the Pakistani phone one. It covers 03XX with hyphen, space, dot or no separator, the +92 and 0092 forms, and brackets. The lookarounds stop it from matching inside longer numbers. For CNICs:

- The hyphenated form scores 0.9.
- A plain 13-digit number scores only 0.3, below the 0.35 threshold, so it needs a context word like 'CNIC' before it. That's a deliberate trade-off against barcodes."

**4:00 Example.** Run:

```powershell
& $py -m pii_pipeline.cli redact --text "Customer Name: Ayesha Khan, CNIC 42101-1234567-1, call 0321-1234567, mail ayesha.k@example.org, House #12, Street 4, Block B, Gulberg, Lahore 54000, account UBW-12345" --dry-run
```

"The dry run shows only masked values. Without --dry-run, every field becomes a placeholder. Notice that spaCy also tagged 'Gulberg' and 'Lahore' as person names inside the address. The overlap handling still replaces the whole address, but the evaluation counts those as false positives."

**4:40 Metrics.** "On the same dataset, the improved pipeline reaches 0.9071 recall, 0.8442 precision and 0.8745 F1:

- CNIC goes from 0 to 0.9606 recall.
- Phones go from 0.9234 to 1.0000.
- Addresses go from 0 to 0.8942.
- Names are still the weakest, at 0.7591 recall and 0.6403 precision.

Whole planted values left in the redacted text drop from 1244 to 236, but 308 occurrences are still not fully covered. One caveat: the false-positive trap rate falls from 0.1859 to 0.0087, but most of that comes from an allow-list written for the generator's own code formats. So I treat it as optimistic."

**5:40 A real miss and its fix.** "Here's DM-001, from the first run: 'NIC:' glued directly to a 13-digit CNIC. spaCy reads that as one token, so Presidio's context enhancer never sees the label, and the number stayed at 0.3. I added a label-anchored pattern, and this regression test now passes. Not everything is fixed. Lower-case, ALL-CAPS and unlabelled names are still missed by the small model. Those cases have strict xfail tests, so if their behaviour changes, the suite tells me."

**6:30 Privacy policy.** "The policy covers:

- local-only processing and data minimisation
- a proposed retention schedule and access control
- no raw PII in logs, with a masking filter as a backup
- keyed HMAC instead of plain hashes, because phone numbers and CNICs are easy to brute-force
- a seven-step incident response

It is a prototype policy, not a legal compliance claim."

**7:05 Tests.** Run `& $py -m pytest -q`. "193 passed and 4 expected failures, the documented name misses. They cover:

- dataset integrity and determinism
- positive and negative recogniser cases
- overlaps, Unicode and residual checks
- hand-checkable metric examples
- that no planted value appears in the logs"

**7:35 Limitations and close.** "The scores are optimistic. I wrote the recognisers knowing the generator's formats, and I found the fixes on the same data. On held-out formats, recall is 0.5784. Landmark addresses aren't detected at all. Next steps:

- a stronger NER model, if the hardware allows
- a reviewer flag for unlabelled 13-digit numbers
- testing on properly governed real-style data

Peer review is still pending. Thanks for watching."

## After recording

- Watch the whole recording and check that no personal information is visible.
- Note the duration and where you uploaded it, then update the README section "Video walkthrough" from PENDING to that link.
- Do not add a link before the video exists.
