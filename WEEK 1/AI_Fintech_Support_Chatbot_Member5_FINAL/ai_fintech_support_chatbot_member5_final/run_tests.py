import csv
from pathlib import Path
from app.model_service import classify_query

BASE_DIR = Path(__file__).resolve().parent
INPUT_FILE = BASE_DIR / "data" / "test_cases.csv"
OUTPUT_FILE = BASE_DIR / "data" / "test_results.csv"


def main():
    with INPUT_FILE.open(newline="", encoding="utf-8") as f:
        tests = list(csv.DictReader(f))

    rows = []
    passed = 0

    for test in tests:
        try:
            result = classify_query(test["query"])
            predicted = result["intent"]
            ok = predicted == test["expected_intent"]
            passed += int(ok)

            rows.append({
                "id": test["id"],
                "query": test["query"],
                "expected_intent": test["expected_intent"],
                "predicted_intent": predicted,
                "confidence": result["confidence"],
                "result": "PASS" if ok else "FAIL",
                "notes": "" if ok else "Review label wording, model choice, or threshold.",
            })
        except Exception as exc:
            rows.append({
                "id": test["id"],
                "query": test["query"],
                "expected_intent": test["expected_intent"],
                "predicted_intent": "ERROR",
                "confidence": "",
                "result": "FAIL",
                "notes": str(exc),
            })

    fieldnames = [
        "id", "query", "expected_intent", "predicted_intent",
        "confidence", "result", "notes"
    ]

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    total = len(tests)
    print(f"Tests passed: {passed}/{total}")
    print(f"Accuracy: {(passed/total):.2%}" if total else "Accuracy: N/A")
    print(f"Results saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
