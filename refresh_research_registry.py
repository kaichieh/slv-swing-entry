from __future__ import annotations

import json

import asset_config as ac
from research_policy import evaluate_policy
from research_profiles import load_research_profile
from research_registry import build_registry_row, write_registry


def main() -> None:
    rows: list[dict[str, object]] = []
    for asset_key in ac.ASSET_DEFAULTS:
        profile = load_research_profile(asset_key)
        metrics = {
            "rows": 0.0,
            "positive_rate": 0.0,
            "baseline_score": 0.0,
            "walkforward_median_bal_acc": 0.0,
            "recent_consistency": 0.0,
            "trade_count": 0.0,
            "max_drawdown_pct": 0.0,
        }
        decision = evaluate_policy(profile.validation_policy, metrics)
        rows.append(build_registry_row(asset_key, profile.__dict__, metrics, decision.__dict__))

    output_path = ac.REPO_DIR / "monitor_registry.tsv"
    write_registry(rows, output_path)
    print(json.dumps({"output_path": str(output_path), "rows": len(rows)}, indent=2))


if __name__ == "__main__":
    main()
