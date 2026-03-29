"""
Backfill and refresh headline_score / gate columns in results.tsv.
"""

from __future__ import annotations

import csv
from pathlib import Path

import asset_config as ac
from research_batch import compute_headline_score, passes_promotion_gate

RESULTS_PATH = Path(ac.get_results_path())
FIELD_ORDER = [
    "commit_id",
    "validation_f1",
    "validation_accuracy",
    "validation_bal_acc",
    "test_f1",
    "test_accuracy",
    "test_bal_acc",
    "headline_score",
    "promotion_gate",
    "status",
    "description",
]


def main() -> None:
    rows: list[dict[str, str]] = []
    with RESULTS_PATH.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            validation_f1 = float(row["validation_f1"])
            validation_bal_acc = float(row["validation_bal_acc"])
            test_f1 = float(row["test_f1"])
            test_bal_acc = float(row["test_bal_acc"])
            row["headline_score"] = f"{compute_headline_score(validation_f1, validation_bal_acc, test_f1, test_bal_acc):.4f}"
            row["promotion_gate"] = "pass" if passes_promotion_gate(validation_bal_acc, test_bal_acc) else "fail"
            rows.append(row)

    with RESULTS_PATH.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_ORDER, delimiter="\t")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELD_ORDER})

    print(f"Updated {RESULTS_PATH} with headline_score and promotion_gate.")


if __name__ == "__main__":
    main()
