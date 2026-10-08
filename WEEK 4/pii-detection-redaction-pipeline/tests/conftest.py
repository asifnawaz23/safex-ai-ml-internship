"""Shared pytest fixtures. src/ is put on sys.path by pytest.ini (pythonpath = src)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pii_pipeline import config  # noqa: E402
from pii_pipeline.synthetic_data import generate_dataset_full  # noqa: E402

TEST_LOG_NAME = "pipeline_test.log"


@pytest.fixture(scope="session", autouse=True)
def _isolated_log_file(tmp_path_factory):
    """Keep test runs out of the real output/pipeline.log.

    Tests that call cli.main() trigger the CLI logging setup, which attaches a
    FileHandler for settings logging.log_file. During the test session that
    path is redirected to a temp file, so output/pipeline.log only contains
    real CLI runs (and the planted-value log scan covers CLI output only).
    """
    log_path = tmp_path_factory.mktemp("logs") / TEST_LOG_NAME
    real_get_path = config.get_path

    def _get_path(key_path):
        return log_path if key_path == "logging.log_file" else real_get_path(key_path)

    mp = pytest.MonkeyPatch()
    mp.setattr(config, "get_path", _get_path)
    yield log_path
    mp.undo()
    import logging
    pkg = logging.getLogger("pii_pipeline")
    for h in list(pkg.handlers):
        if isinstance(h, logging.FileHandler) and h.baseFilename == str(log_path):
            pkg.removeHandler(h)
            h.close()


@pytest.fixture(scope="session")
def full_dataset():
    """Full default dataset (seed 42, 850 planted + challenge records), in memory."""
    return generate_dataset_full(seed=42, count=850)


@pytest.fixture(scope="session")
def small_dataset():
    """60 planted records + challenge records for integration tests."""
    return generate_dataset_full(seed=42, count=60)


@pytest.fixture(scope="session")
def baseline_engine():
    from pii_pipeline.analyzer import build_analyzer
    return build_analyzer("baseline")


@pytest.fixture(scope="session")
def improved_engine():
    from pii_pipeline.analyzer import build_analyzer
    return build_analyzer("improved")


def spans(engine, text, mode="improved"):
    """[(value, label)] of normalised predictions."""
    from pii_pipeline.analyzer import analyze_text
    return [(text[p.start:p.end], p.label) for p in analyze_text(engine, text, mode)]
