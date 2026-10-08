"""Render the README visuals from committed data and captured CLI output.

Usage (Windows PowerShell, from the project root, with the project venv; no PYTHONPATH needed):
    & $py scripts\\render_readme_assets.py                 render every asset
    & $py scripts\\render_readme_assets.py --capture       re-run the read-only CLI commands first
    & $py scripts\\render_readme_assets.py --emit-tables   print the README Markdown tables only

Inputs (read only)
    output/metrics/*.csv, output/metrics/{baseline,improved}_engine.json
    data/generated/{synthetic_documents,ground_truth}.csv, data/generated/dataset_manifest.json
    docs/assets/captures/*.txt and manifest.json (written by --capture)

Outputs (docs/assets/)
    pii-pipeline-hero.svg, pii-pipeline-hero-light.svg  isometric banner, dark and light
    recall_precision_3d.png                             mplot3d bar chart from the metric CSVs
    redaction-before-after.svg                          record REC-00008 before and after redaction
    terminal-{generate,redact,evaluate,pytest}.svg      renders of captured CLI output
    captures/*.txt, captures/manifest.json              only with --capture

Every number in an asset is read from the files above at run time. Terminal images are
renders of captured stdout/stderr, not screenshots. --capture runs only commands that
leave committed artifacts byte-identical (generate, evaluate, redact, pytest -q) and
checks that with SHA-256 hashes; it never runs baseline, improved or all, which rewrite
the runtime figures. The absolute project path is stripped from captured output so only
repo-relative paths remain. Rendering is deterministic: the same inputs give the same bytes.

Exit codes: 0 success, 1 error (message on stderr), 2 invalid arguments (argparse).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "docs" / "assets"
CAPTURES = ASSETS / "captures"
METRICS = ROOT / "output" / "metrics"
DATA = ROOT / "data" / "generated"
RECORD_ID = "REC-00008"
GUARDED_DIRS = ("data/generated", "output/metrics", "output/charts", "output/predictions")

SANS = "Inter, 'Segoe UI', 'Helvetica Neue', Arial, sans-serif"
MONO = "'Cascadia Mono', Consolas, Menlo, 'DejaVu Sans Mono', monospace"

ENTITY_COLOURS = {
    "PERSON": "#F472B6", "EMAIL_ADDRESS": "#60A5FA", "PHONE_NUMBER": "#34D399", "CNIC": "#FBBF24",
    "ADDRESS": "#A78BFA", "POSTAL_CODE": "#FB923C", "CUSTOMER_ID": "#2DD4BF",
}
SHORT_LABELS = {"PHONE_NUMBER": "PHONE", "EMAIL_ADDRESS": "EMAIL", "POSTAL_CODE": "POSTAL",
                "CUSTOMER_ID": "CUST_ID"}
EDGE_TAGS = ("heldout_format", "cnic_plain", "no_context", "phone_local_plain", "unicode_context",
             "three_token_name", "lowercase_name", "uppercase_name", "addr_landmark", "repeated_value")


class AssetError(Exception):
    """Expected failure: missing input, failed capture or failed validation."""


@dataclass(frozen=True)
class CaptureSpec:
    name: str
    argv: tuple
    display: str
    expected_exit: int


CAPTURE_SPECS = (
    CaptureSpec("generate", ("-m", "pii_pipeline.cli", "generate"),
                "& $py -m pii_pipeline.cli generate", 0),
    CaptureSpec("redact_rec00008_baseline",
                ("-m", "pii_pipeline.cli", "redact", "--record-id", RECORD_ID, "--mode", "baseline"),
                f"& $py -m pii_pipeline.cli redact --record-id {RECORD_ID} --mode baseline", 0),
    CaptureSpec("redact_rec00008_improved", ("-m", "pii_pipeline.cli", "redact", "--record-id", RECORD_ID),
                f"& $py -m pii_pipeline.cli redact --record-id {RECORD_ID}", 0),
    CaptureSpec("redact_refused_domain", ("-m", "pii_pipeline.cli", "redact", "--text", "mail someone@gmail.com"),
                '& $py -m pii_pipeline.cli redact --text "mail someone@gmail.com"', 2),
    CaptureSpec("evaluate", ("-m", "pii_pipeline.cli", "evaluate"), "& $py -m pii_pipeline.cli evaluate", 0),
    CaptureSpec("pytest_q", ("-m", "pytest", "-q"), "& $py -m pytest -q", 0),
)
SPEC_BY_NAME = {s.name: s for s in CAPTURE_SPECS}


# ---------------------------------------------------------------------------
# Small I/O helpers
# ---------------------------------------------------------------------------

def rel(path: Path) -> str:
    try:
        return Path(path).resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return Path(path).name


def read_csv(path: Path) -> list:
    if not path.exists():
        raise AssetError(f"missing {rel(path)}")
    with path.open(encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def read_json(path: Path, hint: str = ""):
    if not path.exists():
        raise AssetError(f"missing {rel(path)}{hint}")
    return json.loads(path.read_text(encoding="utf-8"))


def read_capture(name: str) -> str:
    path = CAPTURES / f"{name}.txt"
    if not path.exists():
        raise AssetError(f"missing {rel(path)}; run with --capture first")
    return path.read_text(encoding="utf-8")


def write_bytes_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)
    print(f"wrote {rel(path)} ({len(data)} bytes)")


def write_text_atomic(path: Path, text: str) -> None:
    write_bytes_atomic(path, text.encode("utf-8"))


def hash_tree(dirs) -> dict:
    out = {}
    for d in dirs:
        base = ROOT / d
        if not base.is_dir():
            raise AssetError(f"missing {d}; run & $py -m pii_pipeline.cli all first")
        for p in sorted(base.rglob("*")):
            if p.is_file() and "__pycache__" not in p.parts:
                out[rel(p)] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def index(rows: list, key: str, source: str) -> dict:
    out = {}
    for r in rows:
        if key not in r:
            raise AssetError(f"{source}: column {key} missing")
        out[r[key]] = r
    return out


def need(mapping: dict, key: str, source: str):
    if key not in mapping:
        raise AssetError(f"{source}: {key} missing")
    return mapping[key]


# ---------------------------------------------------------------------------
# Facts (every number used by the assets and tables)
# ---------------------------------------------------------------------------

@dataclass
class Facts:
    comparison: list
    base_rows: list
    imp_rows: list
    summary: dict
    edge: dict
    doc_types: list
    fp_all: dict
    residual_overall: dict
    dangerous: list
    engines: dict
    manifest: dict

    def summary_value(self, metric: str, mode: str) -> str:
        return need(need(self.summary, metric, "experiment_summary.csv"), mode, "experiment_summary.csv")

    def overall(self, mode: str) -> dict:
        rows = self.base_rows if mode == "baseline" else self.imp_rows
        return need(index(rows, "entity_type", f"{mode}_metrics.csv"), "OVERALL", f"{mode}_metrics.csv")


def load_facts() -> Facts:
    comparison = read_csv(METRICS / "comparison.csv")
    base_rows = read_csv(METRICS / "baseline_metrics.csv")
    imp_rows = read_csv(METRICS / "improved_metrics.csv")
    summary = index(read_csv(METRICS / "experiment_summary.csv"), "metric", "experiment_summary.csv")
    edge = {(r["mode"], r["tag"]): r for r in read_csv(METRICS / "edge_case_metrics.csv")}
    doc_types = read_csv(METRICS / "doc_type_metrics.csv")
    fp_all = {r["mode"]: r for r in read_csv(METRICS / "fp_trap_report.csv") if r["trap_kind"] == "ALL"}
    residual_overall = {r["mode"]: r for r in read_csv(METRICS / "residual_pii_report.csv")
                        if r["entity_type"] == "OVERALL"}
    dangerous = read_csv(METRICS / "dangerous_misses.csv")
    engines = {m: read_json(METRICS / f"{m}_engine.json") for m in ("baseline", "improved")}
    manifest = read_json(DATA / "dataset_manifest.json")
    facts = Facts(comparison, base_rows, imp_rows, summary, edge, doc_types, fp_all, residual_overall,
                  dangerous, engines, manifest)
    cross_check_metric_files(facts)
    return facts


def cross_check_metric_files(f: Facts) -> None:
    """comparison.csv must agree with the per-mode metric files it was built from."""
    comp = index(f.comparison, "entity_type", "comparison.csv")
    for mode, rows in (("baseline", f.base_rows), ("improved", f.imp_rows)):
        for r in rows:
            c = need(comp, r["entity_type"], "comparison.csv")
            for col in ("recall", "precision", "f1", "tp", "fn", "fp"):
                if c[f"{mode}_{col}"] != r[col]:
                    raise AssetError(f"comparison.csv {r['entity_type']} {mode}_{col}={c[f'{mode}_{col}']} "
                                     f"but {mode}_metrics.csv has {r[col]}")
    for mode in ("baseline", "improved"):
        if f.overall(mode)["gt_count"] != f.summary_value("gt_occurrences", mode):
            raise AssetError("gt_occurrences in experiment_summary.csv differs from the metric files")
    for mode in ("baseline", "improved"):
        if (mode, "heldout_format") not in f.edge:
            raise AssetError("edge_case_metrics.csv: heldout_format missing")


def metric_value(s: str):
    return None if s.strip().upper() == "N/A" else float(s)


# ---------------------------------------------------------------------------
# Record REC-00008
# ---------------------------------------------------------------------------

@dataclass
class RecordFacts:
    record_id: str
    doc_type: str
    text: str
    gts: list            # dicts: annotation_id, entity_type, value, start, end, tags
    redacted: dict       # mode -> redacted line
    scores: dict         # mode -> per_document_metrics row
    residuals: dict      # mode -> residual row count


def redacted_line(capture: str, name: str) -> str:
    lines = capture.splitlines()
    for i, line in enumerate(lines):
        if line == "--- redacted ---" and i + 1 < len(lines):
            return lines[i + 1]
    raise AssetError(f"captures/{name}.txt: no line after '--- redacted ---'")


def load_record(captures: dict) -> RecordFacts:
    docs = [r for r in read_csv(DATA / "synthetic_documents.csv") if r["record_id"] == RECORD_ID]
    if len(docs) != 1:
        raise AssetError(f"synthetic_documents.csv: {RECORD_ID} found {len(docs)} times, expected once")
    text = docs[0]["text"]
    gts = []
    for r in read_csv(DATA / "ground_truth.csv"):
        if r["record_id"] != RECORD_ID:
            continue
        start, end = int(r["start"]), int(r["end"])
        if text[start:end] != r["text"]:
            raise AssetError(f"ground truth offsets do not match text for {r['annotation_id']}")
        gts.append({"annotation_id": r["annotation_id"], "entity_type": r["entity_type"], "value": r["text"],
                    "start": start, "end": end, "tags": r["tags"]})
    if not gts:
        raise AssetError(f"ground_truth.csv: no rows for {RECORD_ID}")
    gts.sort(key=lambda g: g["start"])
    scores = {}
    for r in read_csv(METRICS / "per_document_metrics.csv"):
        if r["record_id"] == RECORD_ID:
            scores[r["mode"]] = r
    for mode in ("baseline", "improved"):
        need(scores, mode, f"per_document_metrics.csv ({RECORD_ID})")
    residuals = {"baseline": 0, "improved": 0}
    for r in read_csv(METRICS / "residual_pii_details.csv"):
        if r["record_id"] == RECORD_ID:
            residuals[r["mode"]] = residuals.get(r["mode"], 0) + 1
    redacted = {mode: redacted_line(captures[f"redact_rec00008_{mode}"], f"redact_rec00008_{mode}")
                for mode in ("baseline", "improved")}
    return RecordFacts(RECORD_ID, docs[0]["doc_type"], text, gts, redacted, scores, residuals)


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def capture_env() -> dict:
    env = dict(os.environ)
    env.pop("PII_PIPELINE_LOG_LEVEL", None)   # capture the default INFO logging
    env.pop("PII_PIPELINE_HMAC_KEY", None)    # never have a key in scope
    env["PYTHONPATH"] = "src" + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONUNBUFFERED"] = "1"             # keep stdout/stderr in their real order
    env["PYTHONIOENCODING"] = "utf-8"
    return env


def normalise_output(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def strip_path_prefixes(text: str) -> tuple:
    """Turn absolute paths under the project root into repo-relative ones."""
    count = 0
    for form in sorted({str(ROOT), ROOT.as_posix()}, key=len, reverse=True):
        text, k = re.subn(re.escape(form) + r"[\\/]", "", text, flags=re.IGNORECASE)
        count += k
        text, k = re.subn(re.escape(form), ".", text, flags=re.IGNORECASE)
        count += k
    return text, count


def check_no_personal_paths(name: str, text: str) -> None:
    home = Path.home()
    lowered = text.lower()
    for form in {str(home), home.as_posix()}:
        if form.lower() in lowered:
            raise AssetError(f"{name}: captured output contains the home directory path")
    if re.search(r"[\\/]" + re.escape(home.name) + r"[\\/]", text, flags=re.IGNORECASE):
        raise AssetError(f"{name}: captured output contains the user folder name as a path segment")


def run_capture(spec: CaptureSpec) -> tuple:
    start = time.perf_counter()
    try:
        proc = subprocess.run([sys.executable, *spec.argv], cwd=ROOT, env=capture_env(),
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=900, check=False)
    except subprocess.TimeoutExpired:
        raise AssetError(f"{spec.name}: timed out after 900 s") from None
    except OSError as exc:
        raise AssetError(f"{spec.name}: could not start ({exc.strerror})") from None
    text = normalise_output(proc.stdout.decode("utf-8", "replace"))
    return text, proc.returncode, round(time.perf_counter() - start, 2)


def overall_lines(evaluate_text: str) -> list:
    return [line.split() for line in evaluate_text.splitlines() if line.startswith("OVERALL ")]


def check_captures(captures: dict, facts: Facts) -> dict:
    """Content assertions: turn a silent mismatch between captures and CSVs into a failure."""
    records = facts.summary_value("records", "improved")
    gen = captures["generate"]
    if f"Generated {records} records" not in gen or "All offsets valid: True" not in gen:
        raise AssetError(f"captures/generate.txt does not report {records} records with valid offsets")
    imp, base = captures["redact_rec00008_improved"], captures["redact_rec00008_baseline"]
    if "--- redacted ---" not in imp or "cnic=[CNIC]" not in redacted_line(imp, "redact_rec00008_improved"):
        raise AssetError("captures/redact_rec00008_improved.txt: CNIC placeholder missing")
    cnic = [r["text"] for r in read_csv(DATA / "ground_truth.csv")
            if r["record_id"] == RECORD_ID and r["entity_type"] == "CNIC"]
    if not cnic or cnic[0] not in redacted_line(base, "redact_rec00008_baseline"):
        raise AssetError("captures/redact_rec00008_baseline.txt: expected the unredacted CNIC after redaction")
    if "Refused:" not in captures["redact_refused_domain"]:
        raise AssetError("captures/redact_refused_domain.txt: no 'Refused:' line")
    py = captures["pytest_q"]
    m = re.search(r"(\d+) passed, (\d+) xfailed", py)
    if not m or re.search(r"\b\d+ (failed|errors?)\b", py):
        raise AssetError("captures/pytest_q.txt: summary is not 'N passed, M xfailed' without failures")
    ev = captures["evaluate"]
    if "Dangerous-miss cases:" not in ev:
        raise AssetError("captures/evaluate.txt: no 'Dangerous-miss cases:' line")
    rows = overall_lines(ev)
    if len(rows) != 2:
        raise AssetError(f"captures/evaluate.txt: expected 2 OVERALL lines, found {len(rows)}")
    comp = need(index(facts.comparison, "entity_type", "comparison.csv"), "OVERALL", "comparison.csv")
    for mode, cols in zip(("baseline", "improved"), rows):
        if cols[1] != facts.summary_value("gt_occurrences", mode):
            raise AssetError(f"evaluate {mode} OVERALL GT {cols[1]} != experiment_summary.csv")
        for pos, metric in ((6, "recall"), (7, "precision"), (8, "f1")):
            if cols[pos] != comp[f"{mode}_{metric}"]:
                raise AssetError(f"evaluate {mode} OVERALL {metric} {cols[pos]} != comparison.csv "
                                 f"{comp[f'{mode}_{metric}']}")
    return {"passed": int(m.group(1)), "xfailed": int(m.group(2))}


def capture_all(facts: Facts) -> None:
    before = hash_tree(GUARDED_DIRS)
    results = []
    for spec in CAPTURE_SPECS:
        print(f"capturing {spec.name} ...", flush=True)
        text, code, seconds = run_capture(spec)
        if code != spec.expected_exit:
            raise AssetError(f"{spec.name} exited {code}, expected {spec.expected_exit}")
        text, stripped = strip_path_prefixes(text)
        check_no_personal_paths(spec.name, text)
        results.append((spec, text, code, seconds, stripped))
    after = hash_tree(GUARDED_DIRS)
    changed = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    if changed:
        raise AssetError("committed artifacts changed during capture; do not commit, inspect: " + ", ".join(changed))
    print(f"hash guard: {len(after)} files under {', '.join(GUARDED_DIRS)} unchanged")
    counts = check_captures({s.name: t for s, t, *_ in results}, facts)
    print(f"pytest capture: {counts['passed']} passed, {counts['xfailed']} xfailed")
    manifest = {
        "captured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "note": "Raw merged stdout/stderr of each command, CRLF normalised, trailing spaces stripped, "
                "absolute project-root prefixes replaced by repo-relative paths.",
        "hash_guard": {"dirs": list(GUARDED_DIRS), "files": len(after), "unchanged": True},
        "captures": [{"file": f"{s.name}.txt", "display_command": s.display, "argv": list(s.argv),
                      "exit_code": code, "expected_exit_code": s.expected_exit, "seconds": seconds,
                      "path_prefixes_stripped": stripped}
                     for s, _t, code, seconds, stripped in results],
    }
    for spec, text, *_ in results:
        write_text_atomic(CAPTURES / f"{spec.name}.txt", text)
    write_text_atomic(CAPTURES / "manifest.json", json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# SVG primitives
# ---------------------------------------------------------------------------

def num(v: float) -> str:
    s = f"{v:.2f}".rstrip("0").rstrip(".")
    return "0" if s in ("-0", "") else s


def esc(s: str) -> str:
    s = "".join(ch for ch in s if ch in "\t\n" or ord(ch) >= 32)
    return escape(s, {'"': "&quot;"})


def mono(x: float, y: float, s: str, adv: float, cls: str = "m", fill: str = "#C9D1D9",
         bold: bool = False, extra: str = "") -> str:
    """One monospace run stretched to exactly len(s) * adv, so columns align in any font."""
    weight = ' font-weight="700"' if bold else ""
    return (f'<text x="{num(x)}" y="{num(y)}" class="{cls}" fill="{fill}"{weight} textLength="{num(len(s) * adv)}" '
            f'lengthAdjust="spacingAndGlyphs" xml:space="preserve"{extra}>{esc(s)}</text>')


def svg_doc(width: int, height: int, title: str, desc: str, defs: str, style: str, body: list) -> str:
    return "\n".join([
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{esc(title)}</title>',
        f'<desc id="desc">{esc(desc)}</desc>',
        f"<defs>{defs}</defs>",
        f"<style>{style}</style>",
        *body,
        "</svg>",
        "",
    ])


def validate_svg(path: Path, must_contain=()) -> None:
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AssetError(f"{rel(path)}: has a BOM")
    try:
        root = ET.fromstring(raw)
    except ET.ParseError as exc:
        raise AssetError(f"{rel(path)}: not well-formed XML ({exc})") from None
    if root.tag != "{http://www.w3.org/2000/svg}svg":
        raise AssetError(f"{rel(path)}: root element is not svg")
    text = raw.decode("utf-8")
    for banned in ("<script", "<foreignObject", "<image", "href=", "@import", "url(http", "@font-face"):
        if banned.lower() in text.lower():
            raise AssetError(f"{rel(path)}: contains {banned}")
    for s in must_contain:
        if esc(s) not in text:
            raise AssetError(f"{rel(path)}: expected text {s!r} missing")


# ---------------------------------------------------------------------------
# Terminal renders
# ---------------------------------------------------------------------------

T_MARGIN, T_BAR, T_PAD, T_FS, T_ADV, T_LH, T_WRAP, T_MIN_W = 24, 38, 22, 15, 9.0, 22, 110, 960
T_DEFAULT, T_DIM = "#C9D1D9", "#6E7681"
LINE_RULES = (
    (re.compile(r"^(INFO|WARNING|DEBUG) "), "#8B949E", False),
    (re.compile(r"^Refused:"), "#FF7B72", False),
    (re.compile(r"^(Error|ERROR)"), "#FF7B72", False),
    (re.compile(r"^(--- redacted ---$|Evaluation summary)"), "#D2A8FF", True),
)
SPAN_RULES = (
    (re.compile(r"\[(PERSON|EMAIL|PHONE|CNIC|ADDRESS|POSTAL_CODE|CUSTOMER_ID|REDACTED)\]"), "#79C0FF", True),
    (re.compile(r"value='[^']*'"), "#E3B341", False),
    (re.compile(r"\b\d+ passed\b"), "#3FB950", True),
    (re.compile(r"\b\d+ xfailed\b"), "#D29922", True),
    (re.compile(r"\b\d+ (failed|errors?)\b"), "#F85149", True),
)
LEAK = "leak"


def colour_segments(line: str, leaks=()) -> list:
    """Split a line into (start, end, colour, bold) runs. Presentation only; text is unchanged."""
    for rx, colour, bold in LINE_RULES:
        if rx.search(line):
            return [(0, len(line), colour, bold)] if line else []
    base, base_bold = ("#E6EDF3", True) if line.startswith("OVERALL ") else (T_DEFAULT, False)
    found = []
    for value in leaks:
        for m in re.finditer(re.escape(value), line):
            found.append((m.start(), m.end(), LEAK, True))
    for rx, colour, bold in SPAN_RULES:
        for m in rx.finditer(line):
            found.append((m.start(), m.end(), colour, bold))
    segs, pos = [], 0
    for start, end, colour, bold in sorted(found, key=lambda s: s[0]):
        if start < pos:
            continue
        if start > pos:
            segs.append((pos, start, base, base_bold))
        segs.append((start, end, colour, bold))
        pos = end
    if pos < len(line):
        segs.append((pos, len(line), base, base_bold))
    return segs


def wrap_ranges(line: str, width: int) -> list:
    """Break a long line at a space near the limit (hard break if none); returns (start, end) pairs."""
    ranges, start, limit = [], 0, width
    while len(line) - start > limit:
        cut = line.rfind(" ", start + int(limit * 0.6), start + limit + 1)
        if cut <= start:
            cut, nxt = start + limit, start + limit
        else:
            nxt = cut + 1
        ranges.append((start, cut))
        start, limit = nxt, width - 2
    ranges.append((start, len(line)))
    return ranges


@dataclass
class TermBlock:
    display: str
    lines: list
    leaks: tuple = ()
    note: str = ""


def render_terminal_svg(blocks: list, meta: str, title: str, desc: str) -> str:
    rows = []   # each row: list of (col, text, colour, bold, is_leak)
    for bi, block in enumerate(blocks):
        if bi:
            rows.append([])
        rows.append([(0, "PS> ", "#3FB950", True, False), (4, block.display, "#E6EDF3", False, False)])
        for line in block.lines:
            line = line.expandtabs(8)
            segs = colour_segments(line, block.leaks)
            for ri, (rs, re_) in enumerate(wrap_ranges(line, T_WRAP)):
                offset = 0 if ri == 0 else 2
                row = [] if ri == 0 else [(0, "\u21aa ", T_DIM, False, False)]
                for s, e, colour, bold in segs:
                    a, b = max(s, rs), min(e, re_)
                    if a < b:
                        is_leak = colour == LEAK
                        row.append((a - rs + offset, line[a:b], "#FFA198" if is_leak else colour, bold, is_leak))
                rows.append(row)
        if block.note:
            rows.append([(0, block.note, T_DIM, False, False)])
    cols = max([c + len(t) for row in rows for c, t, *_ in row] + [1])
    width = max(T_MIN_W, math.ceil(2 * T_MARGIN + 2 * T_PAD + T_ADV * cols))
    height = 2 * T_MARGIN + T_BAR + 26 + len(rows) * T_LH + 16
    x0, y0 = T_MARGIN + T_PAD, T_MARGIN + T_BAR + 26
    wx, wy, ww, wh = T_MARGIN, T_MARGIN, width - 2 * T_MARGIN, height - 2 * T_MARGIN
    body = [
        f'<rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="14" fill="#0D1117" filter="url(#sh)"/>',
        f'<g clip-path="url(#win)"><rect x="{wx}" y="{wy}" width="{ww}" height="{T_BAR}" fill="#161B22"/></g>',
        f'<line x1="{wx}" y1="{wy + T_BAR}" x2="{wx + ww}" y2="{wy + T_BAR}" stroke="#30363D"/>',
        f'<rect x="{wx + 0.5}" y="{wy + 0.5}" width="{ww - 1}" height="{wh - 1}" rx="14" fill="none" stroke="#30363D"/>',
    ]
    for i, colour in enumerate(("#FF5F56", "#FFBD2E", "#27C93F")):
        body.append(f'<circle cx="{wx + 22 + 20 * i}" cy="{wy + T_BAR / 2}" r="6" fill="{colour}"/>')
    body.append(f'<text x="{width / 2}" y="{wy + 24}" class="s" font-size="13" fill="#8B949E" '
                f'text-anchor="middle">Windows PowerShell \u00b7 pii-detection-redaction-pipeline</text>')
    body.append(f'<text x="{wx + ww - 16}" y="{wy + 24}" class="s" font-size="12" fill="#6E7681" '
                f'text-anchor="end">{esc(meta)}</text>')
    for ri, row in enumerate(rows):
        y = y0 + ri * T_LH
        for col, text, colour, bold, is_leak in row:
            x = x0 + col * T_ADV
            if is_leak:
                body.append(f'<rect x="{num(x - 3)}" y="{num(y - 14)}" width="{num(len(text) * T_ADV + 6)}" '
                            f'height="19" rx="4" fill="#7F1D1D" stroke="#EF4444"/>')
            if text.strip():
                body.append(mono(x, y, text, T_ADV, fill=colour, bold=bold))
    defs = (f'<clipPath id="win"><rect x="{wx}" y="{wy}" width="{ww}" height="{wh}" rx="14"/></clipPath>'
            '<filter id="sh" x="-5%" y="-5%" width="110%" height="115%">'
            '<feDropShadow dx="0" dy="8" stdDeviation="8" flood-color="#010409" flood-opacity=".45"/></filter>')
    style = f".m{{font-family:{MONO};font-size:{T_FS}px;white-space:pre}}.s{{font-family:{SANS}}}"
    return svg_doc(width, height, title, desc, defs, style, body)


def terminal_meta(manifest: dict, names: list) -> str:
    entries = {e["file"]: e for e in manifest.get("captures", [])}
    codes = []
    for n in names:
        e = need(entries, f"{n}.txt", "captures/manifest.json")
        codes.append(str(e["exit_code"]))
    return f"captured {manifest['captured_at'][:10]} \u00b7 exit {' / '.join(codes)}"


def build_terminals(captures: dict, cap_manifest: dict, rec: RecordFacts) -> dict:
    out = {}
    leaks = tuple(g["value"] for g in rec.gts)

    def block(name, leaks_=(), lines=None, note=""):
        text = captures[name]
        return TermBlock(SPEC_BY_NAME[name].display, lines if lines is not None else text.splitlines(), leaks_, note)

    def make(file, names, blocks, what):
        cmds = "; ".join(SPEC_BY_NAME[n].display for n in names)
        files = ", ".join(f"{n}.txt" for n in names)
        out[file] = render_terminal_svg(
            blocks, terminal_meta(cap_manifest, names), f"Captured terminal output: {cmds}",
            f"{what} Rendered from docs/assets/captures/{files} by scripts/render_readme_assets.py; "
            "not a screen capture.")

    make("terminal-generate.svg", ["generate"], [block("generate")],
         "Synthetic dataset generation with entity counts, trap count and file hashes.")
    make("terminal-redact.svg",
         ["redact_rec00008_baseline", "redact_rec00008_improved", "redact_refused_domain"],
         [block("redact_rec00008_baseline", leaks), block("redact_rec00008_improved", leaks),
          block("redact_refused_domain")],
         f"Record {RECORD_ID} redacted in baseline mode (the CNIC stays in the text) and in improved mode "
         "(all four values replaced), then a refused input with a non-example email domain (exit 2).")
    ev = captures["evaluate"].splitlines()
    cut = next(i for i, line in enumerate(ev) if line.startswith("Dangerous-miss cases:"))
    rest = len(ev) - cut - 1
    note = (f"\u2026 {rest} more lines: paths of the written files (full output in "
            "docs/assets/captures/evaluate.txt)") if rest else ""
    make("terminal-evaluate.svg", ["evaluate"], [block("evaluate", lines=ev[:cut + 1], note=note)],
         "Evaluation summary for both modes: per-entity exact-span metrics, FP-trap hits and dangerous misses.")
    make("terminal-pytest.svg", ["pytest_q"], [block("pytest_q")], "Full pytest suite, quiet mode.")
    return out


# ---------------------------------------------------------------------------
# Before/after card
# ---------------------------------------------------------------------------

B_W, B_X, B_PW, B_PADX, B_FS, B_ADV, B_LH = 1280, 40, 1200, 28, 20, 12.0, 50
CHIP_FS, CHIP_ADV = 13, 7.8
PLACEHOLDER_RX = re.compile(r"\[[A-Z_]+\]")


def wrap_at_fields(text: str, max_cols: int) -> list:
    """Greedy wrap after '; ' field boundaries. Returns (line, start offset) pairs."""
    parts, start = [], 0
    for m in re.finditer(r"; ", text):
        parts.append((start, m.end()))
        start = m.end()
    parts.append((start, len(text)))
    lines, cur_start, cur_end = [], parts[0][0], parts[0][0]
    for s, e in parts:
        if e - cur_start > max_cols and cur_end > cur_start:
            lines.append((text[cur_start:cur_end].rstrip(), cur_start))
            cur_start = s
        cur_end = e
    lines.append((text[cur_start:cur_end].rstrip(), cur_start))
    return lines


def find_placeholders(text: str) -> list:
    return [(m.start(), m.end()) for m in PLACEHOLDER_RX.finditer(text)]


def chip(x: float, y: float, label: str, stroke: str, fill: str, text_fill: str, h: int = 30) -> tuple:
    w = len(label) * CHIP_ADV + 28
    svg = (f'<rect x="{num(x)}" y="{num(y)}" width="{num(w)}" height="{h}" rx="{h // 2}" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="1.5"/>'
           + mono(x + 14, y + h / 2 + 4.5, label, CHIP_ADV, cls="c", fill=text_fill, bold=True))
    return svg, w


def render_panel(py: float, name: str, name_stroke: str, badge: str, state: str, text: str,
                 marks: list) -> tuple:
    """marks: (start, end, kind, entity) in text offsets; kind in gt | ph | leak."""
    lines = wrap_at_fields(text, 72)
    height = 136 + (len(lines) - 1) * B_LH
    out = [f'<rect x="{B_X + 8}" y="{num(py + 8)}" width="{B_PW}" height="{num(height)}" rx="16" fill="#020617" '
           'opacity=".7"/>',
           f'<rect x="{B_X}" y="{num(py)}" width="{B_PW}" height="{num(height)}" rx="16" fill="#111A2E" '
           'stroke="#22304A" stroke-width="1.5"/>']
    svg, _w = chip(B_X + B_PADX, py + 20, name, name_stroke, "#0B1220", "#E2E8F0")
    out.append(svg)
    bstroke, bfill, btext = {"neutral": ("#475569", "#0B1220", "#CBD5E1"), "bad": ("#EF4444", "#450A0A", "#FECACA"),
                             "good": ("#22C55E", "#052E16", "#DCFCE7")}[state]
    bw = len(badge) * CHIP_ADV + 28
    svg, _w = chip(B_X + B_PW - B_PADX - bw, py + 20, badge, bstroke, bfill, btext)
    out.append(svg)
    tx = B_X + B_PADX
    for li, (line, lstart) in enumerate(lines):
        y = py + 100 + li * B_LH
        lend = lstart + len(line)
        local = sorted((max(s, lstart) - lstart, min(e, lend) - lstart, kind, ent)
                       for s, e, kind, ent in marks if s < lend and e > lstart)
        pos = 0
        for s, e, kind, ent in local:
            if s > pos:
                out.append(mono(tx + pos * B_ADV, y, line[pos:s], B_ADV, cls="b", fill="#CBD5E1"))
            bx, bw_ = tx + s * B_ADV - 1.5, (e - s) * B_ADV + 3
            colour = ENTITY_COLOURS.get(ent, "#94A3B8")
            if kind == "gt":
                out.append(f'<rect x="{num(bx)}" y="{num(y - 19)}" width="{num(bw_)}" height="27" rx="6" '
                           f'fill="{colour}" fill-opacity=".18" stroke="{colour}" stroke-width="1.5"/>')
                out.append(mono(tx + s * B_ADV, y, line[s:e], B_ADV, cls="b", fill=colour, bold=True))
                label = ent
                lfill = colour
            elif kind == "ph":
                out.append(f'<rect x="{num(bx)}" y="{num(y - 19)}" width="{num(bw_)}" height="27" rx="6" '
                           'fill="#1E3A8A" stroke="#3B82F6" stroke-width="1.5"/>')
                out.append(mono(tx + s * B_ADV, y, line[s:e], B_ADV, cls="b", fill="#DBEAFE", bold=True))
                label = ""
            else:
                out.append(f'<g class="leak"><rect x="{num(bx)}" y="{num(y - 19)}" width="{num(bw_)}" height="27" '
                           'rx="6" fill="#7F1D1D" stroke="#EF4444" stroke-width="2"/></g>')
                out.append(mono(tx + s * B_ADV, y, line[s:e], B_ADV, cls="b", fill="#FECACA", bold=True))
                label = f"LEAKED \u00b7 {ent}"
                lfill = "#F87171"
            if label:
                lw = len(label) * 6.6
                cx = bx + bw_ / 2
                out.append(mono(cx - lw / 2, y - 25, label, 6.6, cls="l", fill=lfill, bold=True))
            pos = e
        if pos < len(line):
            out.append(mono(tx + pos * B_ADV, y, line[pos:], B_ADV, cls="b", fill="#CBD5E1"))
    return out, height


def leak_marks(redacted: str, gts: list) -> list:
    marks = []
    for g in gts:
        start = redacted.find(g["value"])
        while start != -1:
            marks.append((start, start + len(g["value"]), "leak", g["entity_type"]))
            start = redacted.find(g["value"], start + 1)
    return marks


def render_before_after_svg(rec: RecordFacts, facts: Facts) -> str:
    seed = facts.manifest["seed"]
    n_base = len(facts.engines["baseline"]["recognizers"])
    n_imp = len(facts.engines["improved"]["recognizers"])
    n_custom = len(facts.engines["improved"]["custom_recognizers"])
    body = []
    y = 40
    body.append(f'<text x="{B_X}" y="{y + 24}" class="s" font-size="26" font-weight="800" fill="#F8FAFC">'
                'One record, two pipelines</text>')
    sub = f"{rec.record_id} \u00b7 {rec.doc_type} \u00b7 {len(rec.text)} characters \u00b7 {len(rec.gts)} planted values"
    body.append(mono(B_X, y + 52, sub, 8.4, cls="sub", fill="#94A3B8"))
    stamp = f"SYNTHETIC \u00b7 SEED {seed} \u00b7 VALUES ARE FICTIONAL"
    sw = len(stamp) * CHIP_ADV + 28
    svg, _ = chip(B_X + B_PW - sw, y + 6, stamp, "#F59E0B", "#1C1408", "#FDE68A")
    body.append(svg)
    py = y + 80

    panels = []
    gt_marks = [(g["start"], g["end"], "gt", g["entity_type"]) for g in rec.gts]
    panels.append(("ORIGINAL \u00b7 synthetic input", "#64748B", f"{len(rec.gts)} planted PII \u00b7 ground truth",
                   "neutral", rec.text, gt_marks))
    for mode, name, stroke in (("baseline", f"BASELINE \u00b7 default Presidio \u00b7 {n_base} recognisers", "#90A4AE"),
                               ("improved", f"IMPROVED \u00b7 + {n_custom} custom recognisers \u00b7 {n_imp} total",
                                "#42A5F5")):
        sc, red = rec.scores[mode], rec.redacted[mode]
        r = rec.residuals[mode]
        badge = f"{sc['tp']}/{sc['gt_count']} exact TP \u00b7 {sc['fn']} FN \u00b7 {sc['fp']} FP \u00b7 residual {r}"
        state = "bad" if (int(sc["fn"]) > 0 or r > 0) else "good"
        marks = [(s, e, "ph", "") for s, e in find_placeholders(red)] + leak_marks(red, rec.gts)
        panels.append((name, stroke, badge, state, red, marks))
    captions = ("Presidio AnalyzerEngine \u2192 AnonymizerEngine \u00b7 baseline",
                f"same input \u00b7 improved: {n_imp - n_custom} built-in + {n_custom} custom recognisers")
    for i, (name, stroke, badge, state, text, marks) in enumerate(panels):
        svg, h = render_panel(py, name, stroke, badge, state, text, marks)
        body.extend(svg)
        py += h
        if i < len(panels) - 1:
            cy = py + 26
            body.append(f'<path d="M{B_W / 2 - 9},{num(cy - 5)} L{B_W / 2},{num(cy + 4)} L{B_W / 2 + 9},{num(cy - 5)}" '
                        'fill="none" stroke="#67E8F9" stroke-width="2.5" stroke-linecap="round" '
                        'stroke-linejoin="round"/>')
            body.append(mono(B_W / 2 + 24, cy + 4, captions[i], 7.8, cls="c", fill="#94A3B8"))
            py += 52
    ly = py + 40
    x = B_X
    ents = []
    for g in rec.gts:
        if g["entity_type"] not in ents:
            ents.append(g["entity_type"])
    legend = [(e, ENTITY_COLOURS.get(e, "#94A3B8"), ENTITY_COLOURS.get(e, "#94A3B8")) for e in ents]
    legend += [("placeholder (redacted)", "#3B82F6", "#1E3A8A"), ("leaked: planted value still in output",
                                                                  "#EF4444", "#7F1D1D")]
    for label, stroke, fill in legend:
        body.append(f'<rect x="{num(x)}" y="{ly - 12}" width="16" height="16" rx="4" fill="{fill}" '
                    f'fill-opacity="{".18" if fill == stroke else "1"}" stroke="{stroke}" stroke-width="1.5"/>')
        body.append(mono(x + 24, ly + 1, label, 7.2, cls="g", fill="#CBD5E1"))
        x += 24 + len(label) * 7.2 + 26
    fy = ly + 34
    foot1 = ("Sources: data/generated/{synthetic_documents,ground_truth}.csv \u00b7 "
             "docs/assets/captures/redact_rec00008_*.txt \u00b7 "
             "output/metrics/{per_document_metrics,residual_pii_details}.csv")
    foot2 = "Rendered by scripts/render_readme_assets.py from real CLI output; not a screen capture."
    body.append(mono(B_X, fy, foot1, 6.6, cls="f", fill="#64748B"))
    body.append(mono(B_X, fy + 18, foot2, 6.6, cls="f", fill="#64748B"))
    height = int(fy + 18 + 26)
    body.insert(0, f'<rect width="{B_W}" height="{height}" rx="24" fill="#0B1220"/>')
    leaked = [g for g in rec.gts if g["value"] in rec.redacted["baseline"]]
    leaked_txt = ", ".join(g["entity_type"] for g in leaked) or "nothing"
    desc = (f"Original synthetic record {rec.record_id} with {len(rec.gts)} planted values; the baseline output "
            f"still contains: {leaked_txt}; the improved output replaces "
            f"{'all values' if not leak_marks(rec.redacted['improved'], rec.gts) else 'some values'} with placeholders.")
    style = (f".b{{font-family:{MONO};font-size:{B_FS}px;white-space:pre}}"
             f".c{{font-family:{MONO};font-size:{CHIP_FS}px;white-space:pre}}"
             f".l{{font-family:{MONO};font-size:11px;letter-spacing:.5px;white-space:pre}}"
             f".g{{font-family:{MONO};font-size:12px;white-space:pre}}"
             f".f{{font-family:{MONO};font-size:11px;white-space:pre}}"
             f".sub{{font-family:{MONO};font-size:14px;white-space:pre}}"
             f".s{{font-family:{SANS}}}"
             ".leak{animation:lk 2.4s ease-in-out infinite}@keyframes lk{50%{opacity:.5}}"
             "@media (prefers-reduced-motion: reduce){.leak{animation:none}}")
    return svg_doc(B_W, height, f"Record {rec.record_id} before and after redaction", desc, "", style, body)


# ---------------------------------------------------------------------------
# Hero banner (dark and light)
# ---------------------------------------------------------------------------

HERO_THEMES = {
    "dark": {
        "bg": ("#070B1A", "#0B1E3F", "#0B3550"), "glow": ("#22D3EE", ".20"), "dots": ("#93C5FD", ".10"),
        "ground": ("#020617", ".5"), "depth": ".55", "eyebrow": "#67E8F9", "title": "#FFFFFF",
        "title2": ("#FFFFFF", "#A5F3FC"), "tagline": "#C7D2FE", "muted": "#94A3B8",
        "pill1": ("#0EA5B7", "#0EA5B7", "#FFFFFF"), "pill2": ("#FFFFFF", "#5EEAD4", "#F0FDFA", ".08"),
        "card": ("#0B1222", ".92", "#1E3A5F"), "card_head": "#94A3B8", "card_text": "#E2E8F0",
        "leader": "#67E8F9", "label1": "#F8FAFC", "label2": "#A5B4FC", "spine": "#67E8F9",
        "leak": ("#7F1D1D", "#EF4444", "#FECACA"), "ok": ("#052E16", "#22C55E", "#DCFCE7"),
        "rim": "#FFFFFF",
    },
    "light": {
        "bg": ("#F8FAFC", "#EEF6FF", "#DDF4FB"), "glow": ("#22D3EE", ".22"), "dots": ("#1E40AF", ".10"),
        "ground": ("#0F172A", ".22"), "depth": ".28", "eyebrow": "#0E7490", "title": "#0F172A",
        "title2": ("#0F172A", "#0E7490"), "tagline": "#3730A3", "muted": "#475569",
        "pill1": ("#0E7490", "#0E7490", "#FFFFFF"), "pill2": ("#FFFFFF", "#0E7490", "#0F172A", ".85"),
        "card": ("#FFFFFF", ".95", "#CBD5E1"), "card_head": "#475569", "card_text": "#0F172A",
        "leader": "#0891B2", "label1": "#0F172A", "label2": "#4338CA", "spine": "#0891B2",
        "leak": ("#FEE2E2", "#DC2626", "#991B1B"), "ok": ("#DCFCE7", "#16A34A", "#166534"),
        "rim": "#FFFFFF",
    },
}
SLABS = (  # top gradient, left face, right face
    (("#5EEAD4", "#14B8A6"), "#0F766E", "#115E59"),
    (("#93C5FD", "#3B82F6"), "#1D4ED8", "#1E3A8A"),
    (("#C4B5FD", "#8B5CF6"), "#6D28D9", "#4C1D95"),
    (("#FDE68A", "#F59E0B"), "#B45309", "#78350F"),
)
H_CX, H_W, H_H, H_T, H_CYS = 820, 150, 75, 22, (104, 212, 320, 428)


def slab_glyph(i: int) -> str:
    if i == 0:
        return ('<g fill="#FFFFFF" opacity=".85"><rect x="-30" y="-15" width="60" height="6" rx="3"/>'
                '<rect x="-30" y="-3" width="44" height="6" rx="3"/><rect x="-30" y="9" width="52" height="6" rx="3"/></g>')
    if i == 1:
        return ('<g fill="none" stroke="#FFFFFF" stroke-linecap="round" opacity=".85">'
                '<circle cx="-6" cy="-6" r="16" stroke-width="4"/><path d="M6 6 L20 20" stroke-width="6"/></g>')
    if i == 2:
        return ('<g fill="#1E1B4B" opacity=".85"><rect x="-26" y="-17" width="52" height="8" rx="4"/>'
                '<rect x="-26" y="-4" width="40" height="8" rx="4"/><rect x="-26" y="9" width="52" height="8" rx="4"/></g>')
    return ""   # slab 4 gets standing bars instead (bar_prisms), drawn in screen coordinates


def bar_prisms(cx: float, base_y: float) -> str:
    """Three small isometric columns of rising height standing on the evaluation slab."""
    out = ['<g opacity=".92">']
    for k, height in enumerate((14, 24, 34)):
        x, y, hw, hd = cx - 30 + 30 * k, base_y, 9, 4.5
        top = y - height
        out.append(f'<path d="M{x - hw},{top} L{x},{top + hd} L{x},{y + hd} L{x - hw},{y} Z" fill="#FEF3C7"/>'
                   f'<path d="M{x},{top + hd} L{x + hw},{top} L{x + hw},{y} L{x},{y + hd} Z" fill="#FCD34D"/>'
                   f'<path d="M{x},{top - hd} L{x + hw},{top} L{x},{top + hd} L{x - hw},{top} Z" fill="#FFFFFF"/>')
    out.append("</g>")
    return "".join(out)


def render_hero_svg(theme: str, facts: Facts, masked_cnic: str) -> str:
    p = HERO_THEMES[theme]
    seed = facts.manifest["seed"]
    records = facts.summary_value("records", "improved")
    comp = need(index(facts.comparison, "entity_type", "comparison.csv"), "OVERALL", "comparison.csv")
    r_base, r_imp = comp["baseline_recall"], comp["improved_recall"]
    n_base = len(facts.engines["baseline"]["recognizers"])
    n_custom = len(facts.engines["improved"]["custom_recognizers"])
    n_builtin_imp = len(facts.engines["improved"]["recognizers"]) - n_custom
    W, H = 1280, 560
    cx, w, h, t = H_CX, H_W, H_H, H_T

    defs = [
        f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{p["bg"][0]}"/>'
        f'<stop offset=".55" stop-color="{p["bg"][1]}"/><stop offset="1" stop-color="{p["bg"][2]}"/></linearGradient>',
        f'<radialGradient id="glow" cx="66%" cy="50%" r="50%"><stop offset="0" stop-color="{p["glow"][0]}" '
        f'stop-opacity="{p["glow"][1]}"/><stop offset="1" stop-color="{p["glow"][0]}" stop-opacity="0"/></radialGradient>',
        f'<linearGradient id="t2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="{p["title2"][0]}"/>'
        f'<stop offset="1" stop-color="{p["title2"][1]}"/></linearGradient>',
        f'<pattern id="dots" width="28" height="16" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.2" '
        f'fill="{p["dots"][0]}" fill-opacity="{p["dots"][1]}"/><circle cx="16" cy="10" r="1.2" '
        f'fill="{p["dots"][0]}" fill-opacity="{p["dots"][1]}"/></pattern>',
        f'<clipPath id="card"><rect width="{W}" height="{H}" rx="28"/></clipPath>',
        '<filter id="depth" x="-30%" y="-30%" width="160%" height="180%"><feDropShadow dx="0" dy="16" '
        f'stdDeviation="14" flood-color="#020617" flood-opacity="{p["depth"]}"/></filter>',
        '<filter id="blur" x="-50%" y="-200%" width="200%" height="500%"><feGaussianBlur stdDeviation="10"/></filter>',
        '<filter id="pk" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="3" '
        'result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        '<filter id="cardsh" x="-10%" y="-20%" width="120%" height="150%"><feDropShadow dx="0" dy="10" '
        f'stdDeviation="12" flood-color="#020617" flood-opacity="{p["depth"]}"/></filter>',
    ]
    for i, (top, _l, _r) in enumerate(SLABS):
        defs.append(f'<linearGradient id="top{i}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{top[0]}"/>'
                    f'<stop offset="1" stop-color="{top[1]}"/></linearGradient>')

    body = [f'<g clip-path="url(#card)">',
            f'<rect width="{W}" height="{H}" fill="url(#bg)"/>',
            f'<rect width="{W}" height="{H}" fill="url(#glow)"/>',
            f'<rect x="640" y="0" width="640" height="{H}" fill="url(#dots)"/>',
            f'<ellipse cx="{cx}" cy="528" rx="200" ry="24" fill="{p["ground"][0]}" opacity="{p["ground"][1]}" '
            'filter="url(#blur)"/>',
            f'<line x1="{cx}" y1="{H_CYS[0]}" x2="{cx}" y2="{H_CYS[-1]}" stroke="{p["spine"]}" stroke-opacity=".45" '
            'stroke-width="2" stroke-dasharray="4 6"/>']
    for i in reversed(range(len(SLABS))):
        cy = H_CYS[i]
        _top, left, right = SLABS[i]
        top_d = f"M{cx},{cy - h} L{cx + w},{cy} L{cx},{cy + h} L{cx - w},{cy} Z"
        gy = cy if i == 0 else cy + 22
        body.append(
            f'<g filter="url(#depth)">'
            f'<path d="M{cx - w},{cy} L{cx},{cy + h} L{cx},{cy + h + t} L{cx - w},{cy + t} Z" fill="{left}"/>'
            f'<path d="M{cx},{cy + h} L{cx + w},{cy} L{cx + w},{cy + t} L{cx},{cy + h + t} Z" fill="{right}"/>'
            f'<path d="{top_d}" fill="url(#top{i})"/></g>'
            f'<path d="{top_d}" fill="none" stroke="{p["rim"]}" stroke-opacity=".35"/>'
            f'<path d="{top_d}" fill="#FFFFFF" class="pulse p{i + 1}"/>'
            + (f'<g transform="matrix(0.894 0.447 -0.894 0.447 {cx} {gy})">{slab_glyph(i)}</g>'
               if i < len(SLABS) - 1 else bar_prisms(cx, cy + 44)))
    labels = (("01 SYNTHETIC DATA", f"seed {seed} \u00b7 {records} records"),
              ("02 PRESIDIO ANALYZER", f"{n_builtin_imp} built-in + {n_custom} custom"),
              ("03 ANONYMIZER", "replace operators"),
              ("04 EVALUATION", "exact-span vs ground truth"))
    lx = cx + w + 32
    for (l1, l2), cy in zip(labels, H_CYS):
        body.append(f'<line x1="{cx + w + 6}" y1="{cy}" x2="{cx + w + 24}" y2="{cy}" stroke="{p["leader"]}" '
                    'stroke-opacity=".7" stroke-width="2"/>')
        body.append(f'<circle cx="{cx + w + 6}" cy="{cy}" r="3" fill="{p["leader"]}"/>')
        body.append(f'<text x="{lx}" y="{cy + 2}" class="s" font-size="18" font-weight="800" fill="{p["label1"]}" '
                    f'letter-spacing=".5">{esc(l1)}</text>')
        body.append(f'<text x="{lx}" y="{cy + 24}" class="s" font-size="15" fill="{p["label2"]}">{esc(l2)}</text>')
    body.append(f'<path d="M0,-7 L7,0 L0,7 L-7,0 Z" fill="{p["eyebrow"]}" class="packet" filter="url(#pk)"/>')

    x0 = 72
    body.append(f'<text x="{x0}" y="92" class="s" font-size="15" font-weight="700" letter-spacing="3" '
                f'fill="{p["eyebrow"]}">SAFEX AI/ML INTERNSHIP \u00b7 WEEK 4</text>')
    body.append(f'<text x="{x0}" y="160" class="s" font-size="54" font-weight="800" letter-spacing="-1.5" '
                f'fill="{p["title"]}">PII Detection &amp;</text>')
    body.append(f'<text x="{x0}" y="222" class="s" font-size="54" font-weight="800" letter-spacing="-1.5" '
                'fill="url(#t2)">Redaction Pipeline</text>')
    body.append(f'<text x="{x0}" y="266" class="s" font-size="20" font-weight="500" fill="{p["tagline"]}">'
                'Microsoft Presidio \u00b7 measured recall \u00b7 privacy policy</text>')
    body.append(f'<text x="{x0}" y="298" class="s" font-size="17" fill="{p["muted"]}">'
                'Fictional water company \u00b7 synthetic data \u00b7 runs locally</text>')
    pills = ((f"{records} SYNTHETIC RECORDS", p["pill1"][0], p["pill1"][1], p["pill1"][2], "1"),
             (f"RECALL {r_base} \u2192 {r_imp}", p["pill2"][0], p["pill2"][1], p["pill2"][2], p["pill2"][3]))
    px = x0
    for label, fill, stroke, tfill, fop in pills:
        pw = round(len(label) * 9.4 + 36)
        body.append(f'<rect x="{px}" y="320" width="{pw}" height="42" rx="21" fill="{fill}" fill-opacity="{fop}" '
                    f'stroke="{stroke}" stroke-width="1.5"/>')
        body.append(f'<text x="{px + pw / 2}" y="346" class="s" font-size="15" font-weight="700" letter-spacing=".5" '
                    f'fill="{tfill}" text-anchor="middle">{esc(label)}</text>')
        px += pw + 12

    cfill, cop, cstroke = p["card"]
    body.append(f'<g filter="url(#cardsh)"><rect x="{x0}" y="392" width="560" height="120" rx="16" fill="{cfill}" '
                f'fill-opacity="{cop}" stroke="{cstroke}"/></g>')
    body.append(mono(x0 + 22, 420, f"{RECORD_ID} \u00b7 CNIC FIELD \u00b7 VALUE MASKED IN THIS BANNER", 7.8,
                     cls="ch", fill=p["card_head"], bold=True))
    rows = (("baseline", f"cnic={masked_cnic}", "LEAKED", p["leak"]),
            ("improved", "cnic=[CNIC]", "REDACTED", p["ok"]))
    for ri, (mode, value, tag, (tf, ts, tt)) in enumerate(rows):
        y = 456 + ri * 36
        line = f"{mode}  {value}"
        body.append(mono(x0 + 22, y, line, 10.2, cls="cm", fill=p["card_text"]))
        tx = x0 + 22 + 31 * 10.2 + 14
        tw = len(tag) * 7.8 + 22
        body.append(f'<rect x="{num(tx)}" y="{y - 17}" width="{num(tw)}" height="24" rx="12" fill="{tf}" '
                    f'stroke="{ts}" stroke-width="1.5"/>')
        body.append(mono(tx + 11, y, tag, 7.8, cls="ch", fill=tt, bold=True))
    body.append("</g>")

    title = "PII Detection and Redaction Pipeline"
    desc = (f"Isometric stack of four layers: synthetic data (seed {seed}, {records} records), Presidio Analyzer "
            f"({n_builtin_imp} built-in and {n_custom} custom recognisers), Anonymizer, and evaluation against ground "
            f"truth. Overall recall rose from {r_base} to {r_imp}. A mini card shows a CNIC leaked by the baseline "
            "and redacted by the improved pipeline.")
    first, last = H_CYS[0], H_CYS[-1]
    style = (f".s{{font-family:{SANS}}}"
             f".cm{{font-family:{MONO};font-size:17px;white-space:pre}}"
             f".ch{{font-family:{MONO};font-size:13px;letter-spacing:1px;white-space:pre}}"
             ".packet{opacity:0;animation:drop 4s ease-in-out infinite}"
             f"@keyframes drop{{0%{{transform:translate({cx}px,{first}px);opacity:0}}10%{{opacity:1}}"
             f"90%{{opacity:1}}100%{{transform:translate({cx}px,{last}px);opacity:0}}}}"
             ".pulse{opacity:0;animation:pulse 4s ease-in-out infinite}"
             ".p2{animation-delay:1s}.p3{animation-delay:2s}.p4{animation-delay:3s}"
             "@keyframes pulse{0%,100%{opacity:0}12%{opacity:.28}30%{opacity:0}}"
             "@media (prefers-reduced-motion: reduce){.packet,.pulse{animation:none}.packet{opacity:0}}")
    if n_base != n_builtin_imp:
        raise AssetError("baseline and improved built-in recogniser counts differ; update the hero labels")
    return svg_doc(W, H, title, desc, "".join(defs), style, body)


# ---------------------------------------------------------------------------
# 3D chart
# ---------------------------------------------------------------------------

def render_3d_chart(facts: Facts, path: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    bg, base_c, imp_c = "#0B1220", "#90A4AE", "#42A5F5"
    ents = [r["entity_type"] for r in facts.base_rows]
    if ents != [r["entity_type"] for r in facts.imp_rows] or ents[-1] != "OVERALL":
        raise AssetError("baseline_metrics.csv and improved_metrics.csv rows differ or OVERALL is not last")
    xs = list(range(len(ents) - 1)) + [len(ents) - 1 + 0.6]
    records = facts.summary_value("records", "improved")
    gt = facts.summary_value("gt_occurrences", "improved")
    heldout = facts.edge[("improved", "heldout_format")]["recall"]
    with plt.rc_context({"grid.color": "#24324D", "axes.edgecolor": "#24324D", "font.family": "DejaVu Sans"}):
        fig = plt.figure(figsize=(15, 6.3), dpi=150, facecolor=bg)
        for idx, metric in enumerate(("recall", "precision")):
            ax = fig.add_subplot(1, 2, idx + 1, projection="3d")
            ax.set_facecolor(bg)
            bx, by, bdz, colours, labels = [], [], [], [], []
            for row_y, rows, colour in ((0, facts.base_rows, base_c), (1, facts.imp_rows, imp_c)):
                # Baseline values are printed on the floor in front of the grey bars and improved
                # values on top of the blue bars, so the two rows never print over each other.
                for x, r in zip(xs, rows):
                    v = metric_value(r[metric])
                    s, c = ("N/A", "#FBBF24") if v is None else (f"{v:.2f}", "#E2E8F0" if row_y else "#CBD5E1")
                    if row_y == 0:
                        labels.append((x, -0.5, 0.0, s, c))
                    else:
                        labels.append((x, row_y, (v or 0) + 0.03, s, c))
                    if v is not None and v > 0:
                        bx.append(x - 0.275)
                        by.append(row_y - 0.225)
                        bdz.append(v)
                        colours.append(colour)
            bars = ax.bar3d(bx, by, [0] * len(bx), 0.55, 0.45, bdz, color=colours, shade=True,
                            edgecolor=bg, linewidth=0.3)
            bars.set_clip_on(False)  # the zoomed box extends past the 2D axes box; do not cut bars off
            for x, y, z, s, c in labels:
                ax.text(x, y, z, s, ha="center", va="bottom", fontsize=9, color=c, zorder=10,
                        bbox={"boxstyle": "round,pad=0.18", "fc": bg, "ec": "none", "alpha": 0.78})
            ax.set_xticks(xs)
            ax.set_xticklabels([SHORT_LABELS.get(e, e) for e in ents], fontsize=9, color="#CBD5E1",
                               rotation=0, ha="center")
            ax.set_yticks([0, 1])
            ax.set_yticklabels(["Baseline", "Improved"], fontsize=9, color="#CBD5E1")
            ax.set_zlim(0, 1.1)
            ax.set_zticks([0, 0.25, 0.5, 0.75, 1.0])
            ax.tick_params(colors="#CBD5E1", labelsize=8.5)
            ax.set_xlim(-0.6, xs[-1] + 0.6)
            ax.set_ylim(-0.6, 1.6)
            for axis in (ax.xaxis, ax.yaxis, ax.zaxis):
                axis.set_pane_color((0.067, 0.102, 0.18, 1.0))
            ax.view_init(elev=22, azim=-72)
            ax.set_box_aspect((2.6, 0.9, 0.9), zoom=1.3)
            ax.set_title(f"{metric.capitalize()} (exact span)", color="#F8FAFC", fontsize=14, pad=0, y=0.93)
        fig.suptitle("Per-entity recall and precision: default Presidio vs improved pipeline",
                     color="#F8FAFC", fontsize=17, y=0.975)
        fig.text(0.5, 0.9, f"Exact-span, entity-level \u00b7 {records} synthetic records \u00b7 {gt} planted "
                 f"occurrences \u00b7 in-sample (held-out-format recall, improved: {heldout})",
                 ha="center", color="#94A3B8", fontsize=11)
        fig.legend(handles=[Patch(color=base_c, label="Baseline (default Presidio)"),
                            Patch(color=imp_c, label="Improved (+ custom recognisers, allow-list)")],
                   loc="upper center", bbox_to_anchor=(0.5, 0.88), ncol=2, labelcolor="#E2E8F0",
                   frameon=False, fontsize=10.5)
        fig.text(0.012, 0.05, "Source: output/metrics/baseline_metrics.csv and improved_metrics.csv \u00b7 baseline "
                 "values on the floor in front of the grey bars, improved values on top of the blue bars \u00b7 "
                 "N/A = no predictions, so precision is undefined",
                 color="#94A3B8", fontsize=9.5)
        fig.text(0.012, 0.02, "PHONE = PHONE_NUMBER, EMAIL = EMAIL_ADDRESS, POSTAL = POSTAL_CODE, "
                 "CUST_ID = CUSTOMER_ID \u00b7 the README tables are authoritative \u00b7 rendered by "
                 "scripts/render_readme_assets.py", color="#94A3B8", fontsize=9.5)
        fig.subplots_adjust(left=0.0, right=0.975, bottom=0.08, top=0.87, wspace=0.02)
        tmp = path.with_suffix(".png.tmp")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(tmp, format="png", dpi=150, facecolor=fig.get_facecolor(), metadata={"Software": None})
        plt.close(fig)
    os.replace(tmp, path)
    print(f"wrote {rel(path)} ({path.stat().st_size} bytes)")


def validate_png(path: Path) -> None:
    raw = path.read_bytes()
    if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssetError(f"{rel(path)}: not a PNG")
    if not 50_000 < len(raw) < 800_000:
        raise AssetError(f"{rel(path)}: size {len(raw)} bytes outside 50 KB - 800 KB")


# ---------------------------------------------------------------------------
# Markdown tables for the README (--emit-tables)
# ---------------------------------------------------------------------------

def arrow(a: str, b: str) -> str:
    return f"{a} \u2192 {b}"


def markdown_tables(facts: Facts) -> str:
    out = ["<!-- generated from output/metrics/comparison.csv -->",
           "| Entity | GT | Recall | Precision | F1 | \u0394 recall | Target R / P | Met R / P |",
           "|---|---|---|---|---|---|---|---|"]
    for r in facts.comparison:
        name = r["entity_type"]
        label = f"**{name}**" if name == "OVERALL" else name
        out.append(f"| {label} | {r['gt_count']} | {arrow(r['baseline_recall'], r['improved_recall'])} | "
                   f"{arrow(r['baseline_precision'], r['improved_precision'])} | "
                   f"{arrow(r['baseline_f1'], r['improved_f1'])} | {r['delta_recall']} | "
                   f"{r['target_recall']} / {r['target_precision'] or '\u2014'} | "
                   f"{r['improved_meets_recall_target']} / {r['improved_meets_precision_target'] or '\u2014'} |")

    rec = facts.summary_value("records", "improved")
    bo, io = facts.overall("baseline"), facts.overall("improved")
    fb, fi = facts.fp_all["baseline"], facts.fp_all["improved"]
    rb, ri = facts.residual_overall["baseline"], facts.residual_overall["improved"]
    sv = facts.summary_value
    out += ["", "<!-- generated from *_metrics.csv, fp_trap_report.csv, residual_pii_report.csv, "
                "experiment_summary.csv -->",
            "| Secondary metric | Baseline | Improved |", "|---|---|---|",
            f"| Overlap recall | {bo['overlap_recall']} | {io['overlap_recall']} |",
            f"| Redaction coverage | {bo['redaction_coverage']} | {io['redaction_coverage']} |",
            f"| FP-trap hit rate | {fb['hit_rate']} ({fb['hits']}/{fb['traps']}) | "
            f"{fi['hit_rate']} ({fi['hits']}/{fi['traps']}) |",
            f"| Residual planted values in the redacted text | {sv('residual_values', 'baseline')} | "
            f"{sv('residual_values', 'improved')} |",
            f"| Occurrences not fully redacted | {rb['not_fully_redacted']} | {ri['not_fully_redacted']} |",
            f"| Residual direct-identifier rate (phone, CNIC, email) | "
            f"{sv('residual_direct_identifier_rate', 'baseline')} | {sv('residual_direct_identifier_rate', 'improved')} |",
            f"| Runtime, {rec} records (final-audit run) | {sv('runtime_seconds', 'baseline')} s "
            f"({sv('ms_per_record', 'baseline')} ms/record) | {sv('runtime_seconds', 'improved')} s "
            f"({sv('ms_per_record', 'improved')} ms/record) |"]

    cols = ("gt_count", "pred_count", "tp", "fn", "fp", "recall", "precision", "f1", "partial", "wrong_label",
            "duplicate", "overlap_recall", "redaction_coverage")
    for mode, rows in (("baseline", facts.base_rows), ("improved", facts.imp_rows)):
        out += ["", f"<!-- generated from output/metrics/{mode}_metrics.csv -->",
                "| Entity | GT | Pred | TP | FN | FP | Recall | Precision | F1 | Partial | Wrong label | Duplicate "
                "| Overlap recall | Redaction coverage |",
                "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            name = f"**{r['entity_type']}**" if r["entity_type"] == "OVERALL" else r["entity_type"]
            out.append("| " + " | ".join([name] + [r[c] for c in cols]) + " |")

    out += ["", "<!-- generated from output/metrics/doc_type_metrics.csv -->",
            "| Document type | GT | Recall | Precision | Redaction coverage |", "|---|---|---|---|---|"]
    by = {(r["mode"], r["doc_type"]): r for r in facts.doc_types}
    for dt in sorted({r["doc_type"] for r in facts.doc_types}):
        b, i = by[("baseline", dt)], by[("improved", dt)]
        if b["gt_count"] != i["gt_count"]:
            raise AssetError(f"doc_type_metrics.csv: GT differs between modes for {dt}")
        out.append(f"| {dt} | {b['gt_count']} | {arrow(b['recall'], i['recall'])} | "
                   f"{arrow(b['precision'], i['precision'])} | {arrow(b['redaction_coverage'], i['redaction_coverage'])} |")

    out += ["", "<!-- generated from output/metrics/edge_case_metrics.csv -->",
            "| Edge-case tag | GT | Recall (baseline \u2192 improved) |", "|---|---|---|"]
    for tag in EDGE_TAGS:
        b, i = need(facts.edge, ("baseline", tag), "edge_case_metrics.csv"), facts.edge[("improved", tag)]
        out.append(f"| `{tag}` | {b['gt_count']} | {arrow(b['recall'], i['recall'])} |")

    out += ["", "<!-- generated from output/metrics/dangerous_misses.csv -->",
            "| Case | Entity | Diagnosis | Proposed fix (from the CSV) | Status | Regression test |",
            "|---|---|---|---|---|---|"]
    for r in facts.dangerous:
        test = r["regression_test"].split("::")[-1]
        fix = r["proposed_fix"].replace("|", "\\|")
        out.append(f"| {r['case_id']} | {r['entity_type']} | `{r['diagnosis']}` | {fix} | "
                   f"{r['verification_status']} | `{test}` |")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def render_all(facts: Facts) -> None:
    captures = {s.name: read_capture(s.name) for s in CAPTURE_SPECS}
    cap_manifest = read_json(CAPTURES / "manifest.json", "; run with --capture first")
    counts = check_captures(captures, facts)
    rec = load_record(captures)
    masked = [r["masked_value"] for r in read_csv(METRICS / "residual_pii_details.csv")
              if r["mode"] == "baseline" and r["record_id"] == RECORD_ID and r["entity_type"] == "CNIC"]
    if len(masked) != 1:
        raise AssetError(f"residual_pii_details.csv: expected one baseline CNIC residual for {RECORD_ID}")
    if f"value='{masked[0]}'" not in captures["redact_rec00008_improved"]:
        raise AssetError("masked CNIC in residual_pii_details.csv differs from the CLI's masked preview")
    ASSETS.mkdir(parents=True, exist_ok=True)

    hero_needs = (f"RECALL {facts.overall('baseline')['recall']} \u2192 {facts.overall('improved')['recall']}",
                  masked[0])
    for theme, name in (("dark", "pii-pipeline-hero.svg"), ("light", "pii-pipeline-hero-light.svg")):
        write_text_atomic(ASSETS / name, render_hero_svg(theme, facts, masked[0]))
        validate_svg(ASSETS / name, hero_needs)

    write_text_atomic(ASSETS / "redaction-before-after.svg", render_before_after_svg(rec, facts))
    cnic = next(g["value"] for g in rec.gts if g["entity_type"] == "CNIC")
    validate_svg(ASSETS / "redaction-before-after.svg", ("[CNIC]", cnic, RECORD_ID))

    terminals = build_terminals(captures, cap_manifest, rec)
    needs = {"terminal-generate.svg": ("All offsets valid: True",),
             "terminal-redact.svg": ("Refused:", "[CNIC]", cnic),
             "terminal-evaluate.svg": ("Dangerous-miss cases:",),
             "terminal-pytest.svg": (f"{counts['passed']} passed", f"{counts['xfailed']} xfailed")}
    for name, svg in terminals.items():
        write_text_atomic(ASSETS / name, svg)
        validate_svg(ASSETS / name, needs[name])

    png = ASSETS / "recall_precision_3d.png"
    render_3d_chart(facts, png)
    validate_png(png)
    print("all assets validated")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Render the README visuals (see module docstring).")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--capture", action="store_true",
                       help="re-run generate, redact, evaluate and pytest -q and rewrite docs/assets/captures/")
    group.add_argument("--emit-tables", action="store_true", help="print the README tables and exit")
    args = parser.parse_args(argv)
    try:
        facts = load_facts()
        if args.emit_tables:
            sys.stdout.reconfigure(encoding="utf-8")
            sys.stdout.write(markdown_tables(facts))
            return 0
        if args.capture:
            capture_all(facts)
        render_all(facts)
        return 0
    except (AssetError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
