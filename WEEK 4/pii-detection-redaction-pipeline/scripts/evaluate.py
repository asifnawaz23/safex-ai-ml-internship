"""Evaluate saved baseline + improved predictions. Same as: python -m pii_pipeline.cli evaluate

Usage: .\\.venv\\Scripts\\python.exe scripts\\evaluate.py [--snapshot-initial]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pii_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["evaluate"] + sys.argv[1:]))
