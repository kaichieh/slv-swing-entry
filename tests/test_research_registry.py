import unittest
from pathlib import Path

import pandas as pd

from research_registry import build_registry_row, write_registry


class ResearchRegistryTest(unittest.TestCase):
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
