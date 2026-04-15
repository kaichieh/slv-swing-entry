from __future__ import annotations

import unittest
from typing import Callable, cast
from unittest import mock

import research_regression_recent_chart as rrc


class RegressionRecentChartPayloadTests(unittest.TestCase):
    def test_build_regression_recent_payload_exposes_recent_watchlist_contract(self) -> None:
        rows = [
            {
                "name": "idle-row",
                "date": "2026-04-13",
                "close": 443.21,
                "predicted_return": 0.0098,
                "future_return_60": 0.0311,
                "prediction_percentile": 0.5123,
                "bucket_direction": "upper",
                "bucket_pct": 20.0,
                "bucket_cutoff": 0.5002,
                "selected": False,
            },
            {
                "name": "watch-row",
                "date": "2026-04-14",
                "close": 444.18,
                "predicted_return": 0.0117,
                "future_return_60": 0.0328,
                "prediction_percentile": 0.8431,
                "bucket_direction": "upper",
                "bucket_pct": 20.0,
                "bucket_cutoff": 0.5002,
                "selected": False,
            },
            {
                "name": "selected-row",
                "date": "2026-04-14",
                "close": 445.09,
                "predicted_return": 0.0123,
                "future_return_60": 0.0345,
                "prediction_percentile": 0.8765,
                "bucket_direction": "upper",
                "bucket_pct": 20.0,
                "bucket_cutoff": 0.5002,
                "selected": True,
            },
        ]
        meta = {"latest_date": "2026-04-14", "lookback_days": 1260}

        builder = getattr(rrc, "build_regression_recent_payload", None)
        self.assertIsNotNone(builder, "expected research_regression_recent_chart.build_regression_recent_payload")
        builder = cast(
            Callable[[list[dict[str, object]], dict[str, object]], dict[str, object]],
            builder,
        )

        with mock.patch.object(rrc.ac, "get_asset_key", return_value="qqq"):
            with mock.patch.object(rrc.ac, "get_asset_symbol", return_value="QQQ"):
                payload = builder(rows, meta)

        self.assertEqual(payload["asset_key"], "qqq")
        self.assertEqual(payload["symbol"], "QQQ")
        self.assertEqual(payload["title"], "QQQ Ranking Watchlist")
        self.assertEqual(payload["selected_count"], 1)
        self.assertEqual(
            payload["latest_text"],
            "最近資料 2026-04-14 | 預測報酬=0.0123 | selected=yes",
        )

        payload_rows = cast(list[dict[str, object]], payload["rows"])
        recent_rows = cast(list[dict[str, object]], payload["recent_rows"])
        self.assertEqual(payload_rows, recent_rows)
        self.assertEqual([row["render_state"] for row in payload_rows], ["idle", "watch", "selected"])
        self.assertIsNot(payload_rows, rows)
        self.assertIsNot(recent_rows, rows)
        self.assertIsNot(payload_rows[0], rows[0])
        self.assertNotIn("render_state", rows[0])
        self.assertNotIn("render_state", rows[1])
        self.assertNotIn("render_state", rows[2])
        self.assertEqual(payload_rows[0]["name"], "idle-row")
        self.assertEqual(payload_rows[1]["name"], "watch-row")
        self.assertEqual(payload_rows[2]["name"], "selected-row")


if __name__ == "__main__":
    unittest.main()
