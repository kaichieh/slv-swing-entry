from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd

import refresh_monitor_snapshot as rms


class RefreshMonitorSnapshotTests(unittest.TestCase):
    def test_build_snapshot_marks_overlay_blocked_line_as_watchlist_blocked(self) -> None:
        frame = pd.DataFrame(
            [
                {
                    "line_id": "gld_current_live_mixed_live",
                    "lane_type": "binary_operator",
                    "role": "primary",
                    "preferred": True,
                    "status": "inactive",
                    "recent_selected_count": 37,
                    "latest_date": "2026-04-14",
                    "latest_value": 0.49,
                    "latest_selected": False,
                    "cutoff": 0.486,
                    "last_selected_date": "2026-04-13",
                }
            ]
        )

        with mock.patch.object(rms.pd, "read_csv", return_value=frame):
            with mock.patch.object(rms.ac, "get_asset_key", return_value="gld"):
                with mock.patch.object(rms.ac, "get_asset_symbol", return_value="GLD"):
                    snapshot = rms.build_snapshot()

        row = snapshot.iloc[0]
        self.assertEqual(row["action"], "watchlist_blocked")
        self.assertEqual(row["days_since_last_selected"], 1)
        self.assertIn("buy-point overlay", row["action_note"])


if __name__ == "__main__":
    unittest.main()
