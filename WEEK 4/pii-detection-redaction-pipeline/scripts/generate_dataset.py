"""Generate the synthetic dataset. Same as: python -m pii_pipeline.cli generate

Usage: .\\.venv\\Scripts\\python.exe scripts\\generate_dataset.py [--seed 42] [--count 850]
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pii_pipeline.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main(["generate"] + sys.argv[1:]))
