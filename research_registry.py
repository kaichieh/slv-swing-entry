from __future__ import annotations

from pathlib import Path

import pandas as pd


REGISTRY_COLUMNS = [
    "asset_key",
    "asset_lane",
    "validation_policy",
    "reference_baseline",
    "rows",
    "trade_count",
    "viability",
    "improvement",
    "adoption",
]


def build_registry_row(
    asset_key: str,
    profile: dict[str, object],
    metrics: dict[str, float],
    decision: dict[str, str],
) -> dict[str, object]:
    return {
        "asset_key": asset_key,
        "asset_lane": profile["asset_lane"],
        "validation_policy": profile["validation_policy"],
        "reference_baseline": profile["reference_baseline"],
        "rows": metrics["rows"],
        "trade_count": metrics["trade_count"],
        "viability": decision["viability"],
        "improvement": decision["improvement"],
        "adoption": decision["adoption"],
    }


def write_registry(rows: list[dict[str, object]], output_path: Path) -> None:
    pd.DataFrame(rows, columns=REGISTRY_COLUMNS).to_csv(output_path, sep="\t", index=False)
