from __future__ import annotations

import unittest
from unittest import mock

import chart_signals as cs


class ChartSignalsPayloadTests(unittest.TestCase):
    def test_build_chart_payload_exposes_algorithm_metadata(self) -> None:
        rows = [
            {
                "date": "2026-04-14",
                "close": 445.09,
                "signal": "no_entry",
                "raw_model_signal": "weak_bullish",
                "buy_point_ok": False,
                "buy_point_warnings": "RSI too extended",
                "probability": 0.49,
                "confidence_gap": 0.004,
                "rule_selected": False,
                "rule_name": "top_20pct_reference",
                "rule_cutoff": 0.5002,
                "model_rationale": "14-day RSI is extended",
                "rule_rationale": "Below historical top 20% cutoff",
                "ret_20": -0.0333,
                "ret_60": 0.0514,
                "drawdown_20": -0.0309,
                "sma_gap_20": 0.0417,
                "rsi_14": 70.91,
            }
        ]
        meta = {
            "latest_date": "2026-04-14",
            "lookback_days": 1260,
            "signal_colors": {"no_entry": "#9ca3af"},
            "rule_top_pct": 20.0,
        }

        with mock.patch.object(cs.ac, "get_asset_key", return_value="gld"):
            with mock.patch.object(cs.ac, "get_asset_symbol", return_value="GLD"):
                with mock.patch.object(
                    cs.ac,
                    "load_asset_config",
                    return_value={
                        "asset_key": "gld",
                        "symbol": "GLD",
                        "live_model_family": "hard_gate_two_expert_mixed",
                        "live_label_mode": "future-return-top-bottom-10pct",
                        "default_chart_signal_mode": "execution",
                    },
                ):
                    payload = cs.build_chart_payload(rows, meta)

        self.assertEqual(payload["algorithm_name"], "hard_gate_two_expert_mixed")
        self.assertEqual(payload["label_mode"], "future-return-top-bottom-10pct")
        self.assertEqual(payload["default_chart_signal_mode"], "execution")
        self.assertEqual(payload["generated_date"], "2026-04-14")
        self.assertEqual(payload["reference_rule"], "top_20pct_reference")
        self.assertEqual(payload["legend"], {"no_entry": "#9ca3af"})
        self.assertEqual(payload["rows"], rows)


if __name__ == "__main__":
    unittest.main()
