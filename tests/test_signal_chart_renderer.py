from __future__ import annotations

import unittest
from typing import cast

import signal_chart_renderer as scr


class SignalChartRendererTests(unittest.TestCase):
    def _build_execution_payload(self) -> dict[str, object]:
        return {
            "variant": "signal",
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

    def _build_regression_recent_payload(self) -> dict[str, object]:
        return {
            "variant": "regression",
            "asset_key": "qqq",
            "symbol": "QQQ",
            "algorithm_name": "hard_gate_two_expert_mixed",
            "algorithm_label": "QQQ hard-gate mixed two-expert",
            "model_family": "hard_gate_two_expert_mixed",
            "label_mode": "future-return-top-bottom-10pct",
            "reference_rule": "top_20pct",
            "default_chart_signal_mode": "raw",
            "generated_date": "2026-04-14",
            "latest_summary": {"latest_date": "2026-04-14", "lookback_days": 1260},
            "legend": {
                "selected": "#065f46",
                "watch": "#f59e0b",
                "idle": "#f8d9a0",
            },
            "title": "QQQ Ranking Watchlist",
            "selected_count": 1,
            "latest_text": "最近資料 2026-04-14 | 預測報酬=0.0123 | selected=yes",
            "recent_rows": [
                {
                    "date": "2026-04-14",
                    "close": 445.09,
                    "render_state": "selected",
                    "predicted_return": 0.0123,
                    "future_return_60": 0.0345,
                    "prediction_percentile": 0.8765,
                    "bucket_direction": "upper",
                    "bucket_pct": 20.0,
                    "bucket_cutoff": 0.5002,
                    "selected": True,
                }
            ],
            "rows": [
                {
                    "date": "2026-04-14",
                    "close": 445.09,
                    "render_state": "selected",
                    "predicted_return": 0.0123,
                    "future_return_60": 0.0345,
                    "prediction_percentile": 0.8765,
                    "bucket_direction": "upper",
                    "bucket_pct": 20.0,
                    "bucket_cutoff": 0.5002,
                    "selected": True,
                }
            ],
        }

    def test_render_html_includes_core_execution_mode_contract(self) -> None:
        html = scr.render_html(self._build_execution_payload())

        self.assertIn("hard_gate_two_expert_mixed", html)
        self.assertIn("future-return-top-bottom-10pct", html)
        self.assertIn("top_20pct", html)
        self.assertIn("Algorithm:", html)
        self.assertIn("Model family:", html)
        self.assertIn("Label mode:", html)
        self.assertIn("Reference rule:", html)
        self.assertIn("Signal mode:", html)
        self.assertIn("Generated from:", html)
        self.assertIn('<div id="chart">', html)
        self.assertIn('<div id="tooltip" class="tooltip"></div>', html)
        self.assertIn("execution signal", html)
        self.assertIn("raw model signal", html)
        self.assertIn("Current view: execution signal after buy-point overlay.", html)

    def test_render_html_includes_execution_tooltip_content_contract(self) -> None:
        html = scr.render_html(self._build_execution_payload())

        self.assertIn("buy_point blocked", html)
        self.assertIn("14-day RSI is extended", html)
        self.assertIn("Below historical top 20% cutoff", html)
        self.assertIn("RSI too extended", html)
        self.assertIn("weak_bullish", html)

    def test_render_html_includes_regression_recent_watchlist_shell_contract(self) -> None:
        html = scr.render_html(self._build_regression_recent_payload())

        self.assertIn("recent-panel", html)
        self.assertIn("recent-summary", html)
        self.assertIn("recent-card", html)

    def test_render_html_rejects_contradictory_explicit_variant(self) -> None:
        regression_payload = self._build_regression_recent_payload()
        regression_payload["variant"] = "signal"

        with self.assertRaisesRegex(ValueError, "variant"):
            scr.render_html(regression_payload)

    def test_render_html_uses_safe_variant_fallback_for_unsupported_value(self) -> None:
        fallback_payload = self._build_regression_recent_payload()
        fallback_payload["variant"] = "unsupported"

        fallback_html = scr.render_html(fallback_payload)

        self.assertIn('<div class="recent-panel">', fallback_html)

    def test_render_html_uses_payload_provided_regression_render_state(self) -> None:
        regression_payload = self._build_regression_recent_payload()
        row = cast(list[dict[str, object]], regression_payload["rows"])[0]
        recent_row = cast(list[dict[str, object]], regression_payload["recent_rows"])[0]
        row["selected"] = False
        row["prediction_percentile"] = 0.99
        row["bucket_pct"] = 20.0
        row["render_state"] = "watch"
        recent_row["selected"] = False
        recent_row["render_state"] = "watch"

        html = scr.render_html(regression_payload)

        self.assertIn("const fillKey = row.render_state || 'idle';", html)
        self.assertIn("colors[fillKey] || '#f8d9a0'", html)
        self.assertNotIn("prediction_percentile || 0", html)
        self.assertNotIn("bucket_pct || 0", html)

    def test_render_html_does_not_emit_undefined_render_variant_chart_call(self) -> None:
        html = scr.render_html(self._build_execution_payload())

        self.assertNotIn("renderVariantChart(", html)


if __name__ == "__main__":
    unittest.main()
