"""
Offline validation that does not download the Hugging Face model.
It checks input validation, required files, test count, and Python imports/syntax.
"""
from pathlib import Path
from app.model_service import clean_input, InputValidationError

BASE = Path(__file__).resolve().parent

required = [
    "app/main.py",
    "app/model_service.py",
    "app/config.py",
    "static/index.html",
    "static/styles.css",
    "static/app.js",
    "data/test_cases.csv",
    "README.md",
    "docs/technical_writeup.md",
    "docs/video_script.md",
]

for item in required:
    assert (BASE / item).exists(), f"Missing file: {item}"

assert clean_input("  My transfer is pending  ") == "My transfer is pending"

bad_inputs = ["", "  ", "a", "x" * 501]
for value in bad_inputs:
    try:
        clean_input(value)
        raise AssertionError(f"Bad input was accepted: {value[:20]!r}")
    except InputValidationError:
        pass

import csv
with (BASE / "data/test_cases.csv").open(newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
assert len(rows) >= 10, "At least 10 test cases are required."

print("Offline validation passed.")
print(f"Required files found: {len(required)}")
print(f"Test cases found: {len(rows)}")
print("Input validation checks passed.")
