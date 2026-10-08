"""Run Experiment B (Presidio + custom recognisers). Same as: python -m pii_pipeline.cli improved

Usage: .\\.venv\\Scripts\\python.exe scripts\\run_improved_pipeline.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pii_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["improved"] + sys.argv[1:]))
