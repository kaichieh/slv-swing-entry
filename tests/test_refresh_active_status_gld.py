import json
import unittest
from pathlib import Path
from unittest.mock import patch

import refresh_active_status as ras


class RefreshActiveStatusGldTests(unittest.TestCase):
    def test_build_gld_uses_dynamic_context_stack_metadata(self) -> None:
        payload = {
            "signal_summary": {
                "predicted_label": 1,
                "predicted_probability": 0.4662,
                "decision_threshold": 0.461,
            },
            "latest_raw_date": "2026-04-01",
            "model_summary": {
                "reference_percentile_rule": "top_7.5pct",
            },
            "model_extra_features": [
                "ret_60",
                "sma_gap_60",
                "atr_pct_20_percentile",
                "trend_quality_20",
            ],
        }
        signal_rows = [
            {"date": "2026-03-28", "signal": "no_entry"},
            {"date": "2026-03-31", "signal": "weak_bullish"},
            {"date": "2026-04-01", "signal": "bullish"},
        ]
        tmpdir = Path(__file__).resolve().parent / "_tmp"
        tmpdir.mkdir(exist_ok=True)
        prediction_path = tmpdir / "latest_prediction_test.json"
        prediction_path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: prediction_path.unlink(missing_ok=True))

        with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
            with patch.object(ras, "read_signal_rows_from_cache", return_value=ras.pd.DataFrame(signal_rows)):
                frame = ras.build_gld(tmpdir)

        row = frame.iloc[0]
        self.assertEqual(row["line_id"], "context_stack_live")
        self.assertEqual(row["recent_selected_count"], 2)
        self.assertEqual(row["last_selected_date"], "2026-04-01")
        self.assertIn("context-stack extras", row["usage_note"])
        self.assertIn("top_7.5pct", row["usage_note"])

    def test_build_gld_status_follows_execution_signal_when_overlay_blocks_entry(self) -> None:
        payload = {
            "signal_summary": {
                "signal": "no_entry",
                "predicted_label": 1,
                "predicted_probability": 0.4662,
                "decision_threshold": 0.461,
            },
            "latest_raw_date": "2026-04-01",
            "model_summary": {
                "reference_percentile_rule": "top_7.5pct",
            },
            "model_extra_features": [
                "ret_60",
                "sma_gap_60",
                "atr_pct_20_percentile",
                "trend_quality_20",
            ],
        }
        signal_rows = [
            {"date": "2026-03-28", "signal": "no_entry"},
            {"date": "2026-03-31", "signal": "weak_bullish"},
            {"date": "2026-04-01", "signal": "no_entry"},
        ]
        tmpdir = Path(__file__).resolve().parent / "_tmp"
        tmpdir.mkdir(exist_ok=True)
        prediction_path = tmpdir / "latest_prediction_overlay_test.json"
        prediction_path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: prediction_path.unlink(missing_ok=True))

        with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
            with patch.object(ras, "read_signal_rows_from_cache", return_value=ras.pd.DataFrame(signal_rows)):
                frame = ras.build_gld(tmpdir)

        row = frame.iloc[0]
        self.assertEqual(row["line_id"], "context_stack_live")
        self.assertEqual(row["status"], "inactive")
        self.assertFalse(bool(row["latest_selected"]))
        self.assertEqual(row["last_selected_date"], "2026-03-31")

    def test_build_gld_uses_explicit_line_id_for_hard_gate_two_expert_mixed_live_family(self) -> None:
        payload = {
            "signal_summary": {
                "signal": "weak_bullish",
                "predicted_label": 1,
                "predicted_probability": 0.4662,
                "decision_threshold": 0.461,
            },
            "latest_raw_date": "2026-04-01",
            "model_summary": {
                "model_family": "hard_gate_two_expert_mixed",
                "reference_percentile_rule": "top_20pct",
            },
            "model_extra_features": [
                "ret_60",
                "sma_gap_60",
                "trend_quality_20",
                "percent_up_days_20",
            ],
        }
        signal_rows = [
            {"date": "2026-03-28", "signal": "no_entry"},
            {"date": "2026-03-31", "signal": "weak_bullish"},
            {"date": "2026-04-01", "signal": "weak_bullish"},
        ]
        tmpdir = Path(__file__).resolve().parent / "_tmp"
        tmpdir.mkdir(exist_ok=True)
        prediction_path = tmpdir / "latest_prediction_hard_gate_test.json"
        prediction_path.write_text(json.dumps(payload), encoding="utf-8")
        self.addCleanup(lambda: prediction_path.unlink(missing_ok=True))

        with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
            with patch.object(ras, "read_signal_rows_from_cache", return_value=ras.pd.DataFrame(signal_rows)):
                frame = ras.build_gld(tmpdir)

        row = frame.iloc[0]
        self.assertEqual(row["line_id"], "hard_gate_two_expert_mixed_live")
        self.assertIn("hard-gate mixed two-expert", row["usage_note"])


if __name__ == "__main__":
    unittest.main()
