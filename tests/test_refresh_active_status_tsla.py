import json
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import refresh_active_status as ras


class RefreshActiveStatusTslaTests(unittest.TestCase):
    def test_build_tsla_prefers_live_xgboost_line_when_configured(self) -> None:
        tmpdir = Path(__file__).resolve().parent / "_tmp"
        tmpdir.mkdir(exist_ok=True)

        prediction_path = tmpdir / "tsla_latest_prediction_test.json"
        prediction_payload = {
            "signal_summary": {
                "signal": "bullish",
                "predicted_probability": 0.8123,
                "decision_threshold": 0.7,
            },
            "latest_raw_date": "2026-04-15",
        }
        prediction_path.write_text(json.dumps(prediction_payload), encoding="utf-8")
        self.addCleanup(lambda: prediction_path.unlink(missing_ok=True))

        signal_rows = pd.DataFrame(
            [
                {"date": "2026-04-10", "signal": "no_entry"},
                {"date": "2026-04-14", "signal": "weak_bullish"},
                {"date": "2026-04-15", "signal": "bullish"},
            ]
        )

        with patch.object(ras.ac, "get_live_model_family", return_value="xgboost"):
            with patch.object(ras.ac, "get_latest_prediction_path", return_value=prediction_path):
                with patch.object(ras, "read_signal_rows_from_cache", return_value=signal_rows):
                    frame = ras.build_tsla(tmpdir)

        row = frame.iloc[0]
        self.assertEqual(row["line_id"], "xgboost_tb30_distance_live")
        self.assertTrue(bool(row["preferred"]))
        self.assertEqual(row["recent_selected_count"], 2)
        self.assertEqual(row["last_selected_date"], "2026-04-15")
        self.assertEqual(row["status"], "active")


if __name__ == "__main__":
    unittest.main()
