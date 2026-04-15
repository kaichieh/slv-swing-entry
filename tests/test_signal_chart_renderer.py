from __future__ import annotations

import unittest

import signal_chart_renderer as scr


class SignalChartRendererTests(unittest.TestCase):
    def test_render_html_shows_algorithm_header_and_hover_fields(self) -> None:
        payload = {
            "asset_key": "gld",
            "symbol": "GLD",
            "algorithm_name": "hard_gate_two_expert_mixed",
            "algorithm_label": "GLD hard-gate mixed two-expert",
            "model_family": "hard_gate_two_expert_mixed",
            "label_mode": "future-return-top-bottom-10pct",
            "reference_rule": "top_20pct",
            "default_chart_signal_mode": "execution",
            "generated_date": "2026-04-14",
            "latest_summary": {"latest_date": "2026-04-14", "lookback_days": 1260},
            "legend": {
                "no_entry": "#9ca3af",
                "weak_bullish": "#fde68a",
                "bullish": "#f59e0b",
                "strong_bullish": "#16a34a",
                "very_strong_bullish": "#065f46",
            },
            "rows": [
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
            ],
        }

        html = scr.render_html(payload)

        self.assertIn("hard_gate_two_expert_mixed", html)
        self.assertIn("future-return-top-bottom-10pct", html)
        self.assertIn("top_20pct", html)
        self.assertIn("model_reason=", html)
        self.assertIn("rule_reason=", html)
        self.assertIn("buy_point_note=", html)


if __name__ == "__main__":
    unittest.main()
