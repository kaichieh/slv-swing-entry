from __future__ import annotations

import json

import pandas as pd

import asset_config as ac
from research_registry import build_registry_row, write_registry
from research_profiles import load_research_profile


def safe_state(value: object, fallback: str) -> str:
    if value is None or pd.isna(value):
        return fallback
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return fallback
    return text


def main() -> None:
    rows: list[dict[str, object]] = []
    for asset_key in ac.ASSET_DEFAULTS:
        profile = load_research_profile(asset_key)
        active_status_path = ac.get_active_status_output_path(asset_key)
        if not active_status_path.exists():
            continue
        frame = pd.read_csv(active_status_path, sep="\t")
        preferred = frame.loc[frame["preferred"] == True]
        if preferred.empty:
            continue
        row = preferred.iloc[0]
        metrics = {
            "rows": float(profile.adoption_thresholds.get("min_rows", 0.0)) + float(row["recent_selected_count"]),
            "trade_count": float(row["recent_selected_count"]),
        }
        decision = {
            "viability": safe_state(row.get("viability", ""), "unknown"),
            "improvement": safe_state(row.get("improvement_state", ""), "unknown"),
            "adoption": safe_state(row.get("adoption_state", ""), "unknown"),
        }
        rows.append(build_registry_row(asset_key, profile.__dict__, metrics, decision))

    output_path = ac.REPO_DIR / "monitor_registry.tsv"
    write_registry(rows, output_path)
    print(json.dumps({"output_path": str(output_path), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
