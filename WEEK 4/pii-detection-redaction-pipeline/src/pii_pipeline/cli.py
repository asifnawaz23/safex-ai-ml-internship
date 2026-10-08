"""
cli.py — command-line interface.

Run from the repository root (PowerShell):
    $env:PYTHONPATH = "src"
    .\\.venv\\Scripts\\python.exe -m pii_pipeline.cli <command> [options]

Commands
    generate   [--seed N] [--count N]     synthetic dataset + ground truth + traps + manifest
    baseline                              Experiment A: default Presidio recognisers
    improved                              Experiment B: + custom recognisers
    evaluate   [--snapshot-initial]       metrics CSVs (both modes) + dangerous misses
    reports                               charts
    redact     (--record-id ID | --text TEXT | --file PATH) [--mode M] [--dry-run] [--output PATH]
    test                                  run the pytest suite
    all                                   generate -> baseline -> improved -> evaluate -> reports

Exit codes: 0 success, 1 error, 2 refused by a privacy/validation safeguard.
Console output never includes the full dataset; only counts, ids, paths and
(for redact) a single document.
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

from pii_pipeline import config
from pii_pipeline.privacy import PrivacyGuardError, install_log_filter

logger = logging.getLogger("pii_pipeline")


def _setup_logging() -> None:
    level = os.environ.get("PII_PIPELINE_LOG_LEVEL", config.get("logging.level", "INFO")).upper()
    pkg = logging.getLogger("pii_pipeline")
    if getattr(pkg, "_pii_cli_configured", False):
        return
    pkg.setLevel(getattr(logging, level, logging.INFO))
    console = logging.StreamHandler(sys.stderr)
    console.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    pkg.addHandler(console)
    log_file = config.get_path("logging.log_file")
    log_file.parent.mkdir(parents=True, exist_ok=True)
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    pkg.addHandler(fh)
    install_log_filter(pkg)
    pkg._pii_cli_configured = True


def _rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(config.ROOT))
    except ValueError:
        return str(p)


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------

def cmd_generate(args) -> int:
    from pii_pipeline.pipeline import generate_and_save
    m = generate_and_save(seed=args.seed, count=args.count)
    print(f"Generated {m['total_records']} records ({m['planted_records']} planted + "
          f"{m['challenge_records']} challenge), seed={m['seed']}")
    print(f"Annotations: {m['annotations']} across {len(m['entity_type_counts'])} entity types; "
          f"FP traps: {m['traps']}; records without PII: {m['records_without_pii']}")
    for t, n in m["entity_type_counts"].items():
        print(f"  {t:<15}{n:>6}")
    print("All offsets valid: " + str(m["all_offsets_valid"]))
    for k, f in m["files"].items():
        print(f"  {k:<18} {f['path']}  sha256={f['sha256'][:12]}...")
    return 0


def _run_mode(mode: str) -> int:
    from pii_pipeline.evaluation import evaluate, format_summary
    from pii_pipeline.pipeline import load_dataset, run_experiment, save_experiment
    records, gt, traps = load_dataset()
    print(f"[{mode}] analysing {len(records)} records with Presidio ...")
    result = run_experiment(mode, records, gt)
    paths = save_experiment(result)
    rep = evaluate(gt, result.predictions, traps, {r.record_id: r.doc_type for r in records}, mode)
    print(format_summary(rep))
    print(f"Residual planted values after redaction: {len(result.residuals)}")
    print(f"Runtime: {result.runtime_seconds:.1f} s ({1000 * result.runtime_seconds / len(records):.1f} ms/record), "
          f"engine build {result.engine_build_seconds:.1f} s")
    for k, p in paths.items():
        print(f"  {k:<12} {_rel(p)}")
    return 0


def cmd_baseline(args) -> int:
    return _run_mode("baseline")


def cmd_improved(args) -> int:
    return _run_mode("improved")


def _evaluate_all():
    from pii_pipeline.evaluation import evaluate
    from pii_pipeline.pipeline import load_dataset, load_engine_meta, load_predictions, load_residuals
    records, gt, traps = load_dataset()
    doc_types = {r.record_id: r.doc_type for r in records}
    reports, residuals, metas = {}, {}, {}
    for mode in ("baseline", "improved"):
        reports[mode] = evaluate(gt, load_predictions(mode), traps, doc_types, mode)
        residuals[mode] = load_residuals(mode)
        metas[mode] = load_engine_meta(mode)
    return records, gt, traps, reports, residuals, metas


def cmd_evaluate(args) -> int:
    import json
    from pii_pipeline import dangerous_misses
    from pii_pipeline.evaluation import format_summary
    from pii_pipeline.reporting import write_all_metrics
    records, gt, traps, reports, residuals, metas = _evaluate_all()
    manifest_path = config.dataset_path("manifest_file")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    out = write_all_metrics(reports, residuals, metas, gt, manifest)
    if getattr(args, "snapshot_initial", False):
        snap = dangerous_misses.snapshot_initial(records, gt, reports)
        for k, p in snap.items():
            out[k] = p
    dm = dangerous_misses.build_dangerous_misses(records, gt, reports["improved"])
    out.update(dangerous_misses.save_dangerous_misses(dm))
    for mode in ("baseline", "improved"):
        print(format_summary(reports[mode]))
        print()
    actual = sum(1 for c in dm if not c["constructed"])
    print(f"Dangerous-miss cases: {len(dm)} ({actual} actual, {len(dm) - actual} constructed)")
    for k, p in out.items():
        print(f"  {k:<20} {_rel(p)}")
    return 0


def cmd_reports(args) -> int:
    from pii_pipeline.reporting import plot_precision_recall_comparison, plot_recall_by_entity
    _r, _g, _t, reports, _res, _m = _evaluate_all()
    p1 = plot_recall_by_entity(reports["baseline"], reports["improved"])
    p2 = plot_precision_recall_comparison(reports["baseline"], reports["improved"])
    print("Charts written:")
    print("  " + _rel(p1))
    print("  " + _rel(p2))
    return 0


def cmd_redact(args) -> int:
    from pii_pipeline.analyzer import analyze_text, build_analyzer
    from pii_pipeline.privacy import (
        assert_synthetic_text, ensure_within, preview_detections, validate_user_input_file,
    )
    from pii_pipeline.redactor import redact_text

    if args.record_id:
        from pii_pipeline.pipeline import load_dataset
        records, _gt, _t = load_dataset()
        match = [r for r in records if r.record_id == args.record_id]
        if not match:
            print(f"Record {args.record_id} not found", file=sys.stderr)
            return 1
        text, source = match[0].text, f"record {args.record_id}"
    elif args.text is not None:
        text, source = args.text, "--text"
    else:
        path = validate_user_input_file(args.file)
        text, source = path.read_text(encoding="utf-8"), f"file {path.name}"
    assert_synthetic_text(text)

    engine = build_analyzer(args.mode)
    preds = analyze_text(engine, text, args.mode)
    print(f"Source: {source} | mode: {args.mode} | {len(text)} characters")
    print(preview_detections(text, preds))
    if args.dry_run:
        print("Dry run: no redacted text produced or written.")
        return 0
    red = redact_text(text, preds)
    if args.output:
        out = ensure_within(args.output, config.get_path("output.redacted_dir"))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(red.text, encoding="utf-8")
        print(f"Redacted text written to {_rel(out)} ({red.n_replaced} replacements)")
    else:
        print("--- redacted ---")
        print(red.text)
    return 0


def cmd_test(args) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q"] + list(args.pytest_args or [])
    return subprocess.run(cmd, cwd=str(config.ROOT), check=False).returncode


def cmd_all(args) -> int:
    for step, fn in (("generate", cmd_generate), ("baseline", cmd_baseline), ("improved", cmd_improved),
                     ("evaluate", cmd_evaluate), ("reports", cmd_reports)):
        print(f"\n=== {step} ===")
        code = fn(args)
        if code != 0:
            print(f"Step {step} failed with exit code {code}", file=sys.stderr)
            return code
    return 0


# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="pii_pipeline.cli",
                                description="PII detection & redaction pipeline (synthetic data only)")
    sub = p.add_subparsers(dest="command", required=True)

    g = sub.add_parser("generate", help="generate the synthetic dataset")
    g.add_argument("--seed", type=int, default=config.SEED)
    g.add_argument("--count", type=int, default=config.RECORD_COUNT)
    g.set_defaults(func=cmd_generate)

    sub.add_parser("baseline", help="run Experiment A (default Presidio)").set_defaults(func=cmd_baseline)
    sub.add_parser("improved", help="run Experiment B (custom recognisers)").set_defaults(func=cmd_improved)

    e = sub.add_parser("evaluate", help="evaluate saved predictions of both modes")
    e.add_argument("--snapshot-initial", action="store_true",
                   help="also save the current improved results as the 'before fixes' snapshot")
    e.set_defaults(func=cmd_evaluate)

    sub.add_parser("reports", help="build charts").set_defaults(func=cmd_reports)

    r = sub.add_parser("redact", help="redact one document")
    src = r.add_mutually_exclusive_group(required=True)
    src.add_argument("--record-id")
    src.add_argument("--text")
    src.add_argument("--file", help="text file inside data/")
    r.add_argument("--mode", choices=["baseline", "improved"], default="improved")
    r.add_argument("--dry-run", action="store_true", help="show masked detections only")
    r.add_argument("--output", help="write redacted text to this path (inside output/redacted)")
    r.set_defaults(func=cmd_redact)

    t = sub.add_parser("test", help="run the pytest suite")
    t.add_argument("pytest_args", nargs="*")
    t.set_defaults(func=cmd_test)

    a = sub.add_parser("all", help="generate, run both experiments, evaluate, build charts")
    a.add_argument("--seed", type=int, default=config.SEED)
    a.add_argument("--count", type=int, default=config.RECORD_COUNT)
    a.add_argument("--snapshot-initial", action="store_true")
    a.set_defaults(func=cmd_all)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:  # avoid UnicodeEncodeError for Urdu text on legacy code pages
            stream.reconfigure(errors="replace")
        except (AttributeError, ValueError):
            pass
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging()
    try:
        return int(args.func(args) or 0)
    except PrivacyGuardError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    except (FileNotFoundError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
