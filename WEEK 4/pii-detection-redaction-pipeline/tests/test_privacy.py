"""
Privacy and security safeguards.
Brief test area 20 (no raw PII in ordinary logs) plus path validation,
synthetic-only guard, HMAC pseudonyms, output separation, offline operation,
CLI refusal exit codes and dry-run masking.
"""
import logging
import re
import socket
from pathlib import Path

import pytest

from pii_pipeline import cli, config, pipeline
from pii_pipeline.privacy import (
    PrivacyGuardError, RawTextRedactingFilter, assert_synthetic_rows, assert_synthetic_text,
    ensure_within, keyed_pseudonym, mask_log_text, mask_value, validate_document_text,
    validate_input_path, validate_output_dir_separation, validate_user_input_file,
)

SRC = Path(config.ROOT) / "src" / "pii_pipeline"


# 20. no raw PII in ordinary logs ---------------------------------------------

def test_pipeline_logs_contain_no_planted_values(caplog, small_dataset):
    records, gt, _traps = small_dataset
    subset = records[:25]
    ids = {r.record_id for r in subset}
    sub_gt = [g for g in gt if g.record_id in ids]
    caplog.set_level(logging.DEBUG, logger="pii_pipeline")
    result = pipeline.run_experiment("improved", subset, sub_gt)
    assert result.record_count == 25
    log_text = caplog.text
    assert log_text, "expected some log output"
    leaked = [g.annotation_id for g in sub_gt if len(g.text) >= 5 and g.text in log_text]
    assert leaked == []


def test_log_filter_masks_pii_like_strings():
    rec = logging.LogRecord("pii_pipeline", logging.INFO, __file__, 1,
                            "user %s phone %s cnic %s acct %s",
                            ("ali.khan@example.org", "0321-1234567", "42101-1234567-1", "UBW-12345"), None)
    RawTextRedactingFilter().filter(rec)
    msg = rec.getMessage()
    for raw in ("ali.khan@example.org", "0321-1234567", "42101-1234567-1", "UBW-12345"):
        assert raw not in msg
    assert "[EMAIL]" in msg and "[CNIC]" in msg and "[CUSTOMER_ID]" in msg


def test_mask_log_text_keeps_ordinary_text():
    assert mask_log_text("improved: 200/870 records analysed") == "improved: 200/870 records analysed"


def test_source_never_logs_record_text():
    """Logging calls in src must not interpolate document text variables."""
    pattern = re.compile(r"logger\.\w+\([^)]*\b(rec\.text|text\[|\.text\b)")
    offenders = [p.name for p in SRC.glob("*.py") if pattern.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


# masking ---------------------------------------------------------------------

def test_mask_value():
    assert mask_value("0321-1234567") == "03********67"
    assert mask_value("54000") == "5****"
    assert mask_value("") == ""


# path validation -------------------------------------------------------------

def test_path_traversal_refused(tmp_path):
    root = tmp_path / "allowed"
    root.mkdir()
    outside = tmp_path / "secret.txt"
    outside.write_text("x", encoding="utf-8")
    with pytest.raises(PrivacyGuardError):
        validate_input_path(root / ".." / "secret.txt", root)
    with pytest.raises(PrivacyGuardError):
        ensure_within(outside, root)


def test_disallowed_extension_refused(tmp_path):
    f = tmp_path / "x.exe"
    f.write_text("x", encoding="utf-8")
    with pytest.raises(PrivacyGuardError):
        validate_input_path(f, tmp_path)


def test_user_input_file_must_be_under_data(tmp_path):
    f = tmp_path / "doc.txt"
    f.write_text("hello", encoding="utf-8")
    with pytest.raises(PrivacyGuardError):
        validate_user_input_file(f)


def test_load_dataset_refuses_outside_data_dir(tmp_path):
    with pytest.raises(PrivacyGuardError):
        pipeline.load_dataset(tmp_path)


def test_output_separation():
    root = config.ROOT
    validate_output_dir_separation(root / "data/generated", root / "data/generated", root / "output/redacted")
    with pytest.raises(PrivacyGuardError):
        validate_output_dir_separation(root / "data/generated", root / "data/generated",
                                       root / "data/generated/redacted")


# synthetic-only guard --------------------------------------------------------

def test_synthetic_guard_accepts_reserved_domains():
    assert assert_synthetic_text("mail a.b@example.org or C@EXAMPLE.NET")


@pytest.mark.parametrize("text", ["mail me at someone@gmail.com", "x@company.com.pk"])
def test_synthetic_guard_rejects_real_looking_domains(text):
    with pytest.raises(PrivacyGuardError):
        assert_synthetic_text(text)


def test_rows_must_be_marked_synthetic():
    assert_synthetic_rows([{"synthetic": "true"}])
    with pytest.raises(PrivacyGuardError):
        assert_synthetic_rows([{"synthetic": "true"}, {"synthetic": ""}])


def test_document_length_limit():
    with pytest.raises(PrivacyGuardError):
        validate_document_text("x" * (config.MAX_DOCUMENT_CHARS + 1))
    with pytest.raises(TypeError):
        validate_document_text(123)


# keyed pseudonyms ------------------------------------------------------------

def test_hmac_requires_key(monkeypatch):
    monkeypatch.delenv(config.HMAC_KEY_ENV, raising=False)
    with pytest.raises(RuntimeError):
        keyed_pseudonym("42101-1234567-1")


def test_hmac_deterministic_and_key_dependent(monkeypatch):
    monkeypatch.setenv(config.HMAC_KEY_ENV, "test-key-1")
    a = keyed_pseudonym("0321-1234567")
    assert a == keyed_pseudonym("0321-1234567") and len(a) == 64
    assert a != keyed_pseudonym("0321-1234568")
    assert a != keyed_pseudonym("0321-1234567", key="test-key-2")


# offline operation -----------------------------------------------------------

def test_analysis_makes_no_network_connections(monkeypatch, improved_engine):
    from pii_pipeline.analyzer import analyze_text
    attempts = []

    def _blocked(*args, **kwargs):
        attempts.append(args)
        raise OSError("network disabled in test")
    monkeypatch.setattr(socket.socket, "connect", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    preds = analyze_text(improved_engine, "Email: z.q12@example.net, call 0321-1234567", "improved")
    assert {p.label for p in preds} >= {"EMAIL_ADDRESS", "PHONE_NUMBER"}
    assert attempts == []


def test_no_eval_exec_or_network_imports_in_src():
    banned = re.compile(r"\b(eval|exec)\s*\(|^\s*import (requests|urllib|http)|^\s*from (requests|urllib|http)",
                        re.MULTILINE)
    offenders = [p.name for p in SRC.glob("*.py") if banned.search(p.read_text(encoding="utf-8"))]
    assert offenders == []


# CLI safeguards --------------------------------------------------------------

def test_cli_redact_refuses_real_looking_email(capsys):
    code = cli.main(["redact", "--text", "mail me at someone@gmail.com", "--dry-run"])
    assert code == 2
    assert "someone@gmail.com" not in capsys.readouterr().out


def test_cli_redact_dry_run_masks_values(capsys):
    code = cli.main(["redact", "--text", "Call 0321-1234567 or mail a.b12@example.org", "--dry-run"])
    out = capsys.readouterr().out
    assert code == 0
    assert "0321-1234567" not in out and "a.b12@example.org" not in out
    assert "PHONE_NUMBER" in out and "Dry run" in out


def test_cli_redact_output_must_stay_in_output_redacted(tmp_path, capsys):
    code = cli.main(["redact", "--text", "Call 0321-1234567", "--output", str(tmp_path / "x.txt")])
    assert code == 2


def test_test_runs_do_not_write_to_repo_log_file(capsys):
    """Review finding 6: CLI calls made by tests must log to a temp file, not to
    output/pipeline.log, so the repo log only reflects real CLI runs."""
    assert cli.main(["redact", "--text", "Call 0321-1234567", "--dry-run"]) == 0
    repo_log = str((config.ROOT / config.get("logging.log_file")).resolve())
    files = [h.baseFilename for h in logging.getLogger("pii_pipeline").handlers
             if isinstance(h, logging.FileHandler)]
    assert files, "CLI logging setup should have attached a file handler"
    assert all(Path(f).resolve() != Path(repo_log) for f in files)
