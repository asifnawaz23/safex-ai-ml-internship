"""Run Experiment A (default Presidio recognisers). Same as: python -m pii_pipeline.cli baseline

Usage: .\\.venv\\Scripts\\python.exe scripts\\run_baseline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pii_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["baseline"] + sys.argv[1:]))
