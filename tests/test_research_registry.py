import unittest
from pathlib import Path

import pandas as pd

from refresh_active_status import apply_governance_fields
from research_registry import build_registry_row, write_registry


class ResearchRegistryTest(unittest.TestCase):
    def test_apply_governance_fields_adds_research_columns(self):
        frame = pd.DataFrame(
            [
                {
                    "line_id": "baseline_threshold",
                    "lane_type": "binary_operator",
                    "role": "research_primary",
                    "preferred": True,
                    "status": "active",
                    "recent_selected_count": 12,
                    "latest_date": "2026-04-01",
                    "latest_value": 0.44,
                    "latest_selected": True,
                    "cutoff": 0.38,
                    "last_selected_date": "2026-04-01",
                    "usage_note": "Research-only line",
                }
            ]
        )

        enriched = apply_governance_fields(
            frame,
            asset_key="slv",
            metrics={
                "rows": 4665,
                "positive_rate": 0.39,
                "baseline_score": 0.55,
                "walkforward_median_bal_acc": 0.49,
                "recent_consistency": 0.58,
                "trade_count": 18,
                "max_drawdown_pct": 0.08,
            },
        )

        self.assertEqual(enriched.loc[0, "research_lane"], "macro_defensive_commodity")
        self.assertEqual(enriched.loc[0, "viability"], "viable_with_caution")
        self.assertEqual(enriched.loc[0, "adoption_state"], "keep_as_research_primary")

    def test_registry_row_combines_profile_and_gate_decision(self):
        row = build_registry_row(
            asset_key="slv",
            profile={
                "asset_lane": "macro_defensive_commodity",
                "validation_policy": "macro_default",
                "reference_baseline": "baseline_threshold",
            },
            metrics={
                "rows": 4665,
                "trade_count": 18,
            },
            decision={
                "viability": "viable_with_caution",
                "improvement": "research_only_improvement",
                "adoption": "keep_as_research_primary",
            },
        )

        self.assertEqual(row["asset_key"], "slv")
        self.assertEqual(row["asset_lane"], "macro_defensive_commodity")
        self.assertEqual(row["reference_baseline"], "baseline_threshold")
        self.assertEqual(row["adoption"], "keep_as_research_primary")

    def test_write_registry_creates_expected_columns(self):
        rows = [
            {
                "asset_key": "slv",
                "asset_lane": "macro_defensive_commodity",
                "validation_policy": "macro_default",
                "reference_baseline": "baseline_threshold",
                "rows": 4665,
                "trade_count": 18,
                "viability": "viable_with_caution",
                "improvement": "research_only_improvement",
                "adoption": "keep_as_research_primary",
            }
        ]
        output_dir = Path("tests") / "_tmp"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / "registry.tsv"
        try:
            write_registry(rows, output_path)
            frame = pd.read_csv(output_path, sep="\t")
        finally:
            if output_path.exists():
                output_path.unlink()

        self.assertEqual(
            list(frame.columns),
            [
                "asset_key",
                "asset_lane",
                "validation_policy",
                "reference_baseline",
                "rows",
                "trade_count",
                "viability",
                "improvement",
                "adoption",
            ],
        )


if __name__ == "__main__":
    unittest.main()
