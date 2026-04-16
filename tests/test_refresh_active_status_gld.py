from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import pandas as pd

import refresh_active_status as ras


class RefreshActiveStatusGldTests(unittest.TestCase):
    def test_build_gld_uses_configured_term_panic_line_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cache_dir = Path(tmp)
            latest_prediction_path = cache_dir / "latest_prediction.json"
            latest_prediction_path.write_text(
                json.dumps(
                    {
                        "latest_raw_date": "2026-04-15",
                        "signal_summary": {
                            "signal": "no_entry",
                            "predicted_probability": 0.51,
                            "decision_threshold": 0.49,
                        },
                        "live_operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                        "live_provenance": {
                            "operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                            "left_expert": "dual_context",
                            "right_expert": "context_no_atr",
                            "outer_gate_feature": "atr_pct_20_percentile",
                            "outer_gate_threshold": 0.7,
                            "decision_overlay": "vix_vxv_term_panic_block",
                            "term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                            "term_panic_threshold": 0.9,
                        },
                        "model_summary": {
                            "model_family": "hard_gate_two_expert_mixed",
                            "label_mode": "future-return-top-bottom-10pct",
                            "reference_percentile_rule": "top_20pct",
                            "live_decision_rule": "threshold_plus_buy_point_overlay_plus_vix_vxv_term_panic_block",
                        },
                        "signal_rows": [],
                    }
                ),
                encoding="utf-8",
            )
            signal_rows = pd.DataFrame(
                [
                    {"date": "2026-04-14", "signal": "bullish"},
                    {"date": "2026-04-15", "signal": "no_entry"},
                ]
            )

            with mock.patch.object(
                ras.ac,
                "load_asset_config",
                return_value={
                    "live_operator_line_id": "gld_mixed_vix_vxv_term_panic_live",
                    "live_left_expert": "dual_context",
                    "live_right_expert": "context_no_atr",
                    "live_outer_gate_feature": "atr_pct_20_percentile",
                    "live_outer_gate_threshold": 0.7,
                    "live_term_panic_feature": "vix_vxv_ratio_pct_63_rolling_max_3",
                    "live_term_panic_threshold": 0.9,
                },
            ):
                with mock.patch.object(ras.ac, "get_latest_prediction_path", return_value=latest_prediction_path):
                    with mock.patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                        output = ras.build_gld(cache_dir)

        self.assertEqual(output.loc[0, "line_id"], "gld_mixed_vix_vxv_term_panic_live")
        self.assertIn("threshold_plus_buy_point_overlay_plus_vix_vxv_term_panic_block", output.loc[0, "usage_note"])


if __name__ == "__main__":
    unittest.main()
