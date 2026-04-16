from __future__ import annotations

import unittest
from unittest import mock

import pandas as pd

import refresh_monitor_board as rmb


class RefreshMonitorBoardTests(unittest.TestCase):
    def test_build_html_includes_watchlist_blocked_cards_in_today_section(self) -> None:
        board = pd.DataFrame(
            [
                {
                    "asset_key": "gld",
                    "symbol": "GLD",
                    "preferred_line": "gld_current_live_mixed_live",
                    "lane_type": "binary_operator",
                    "role": "primary",
                    "status": "inactive",
                    "action": "watchlist_blocked",
                    "recent_selected_count": 37,
                    "latest_date": "2026-04-14",
                    "latest_value": 0.49,
                    "latest_selected": False,
                    "cutoff": 0.486,
                    "last_selected_date": "2026-04-13",
                    "days_since_last_selected": 1.0,
                    "action_note": "Preferred line clears threshold, but the buy-point overlay blocks entry today.",
                    "card_family": "operating",
                    "chart_href": ".cache/gld-swing-entry/signal_chart.html",
                    "display_latest_date": "2026-04-14",
                    "signal_color": "#9ca3af",
                    "research_score": None,
                    "research_score_label": None,
                    "research_rule": None,
                    "research_avg_return": None,
                    "research_trade_count": None,
                }
            ]
        )

        html = rmb.build_html(board)

        self.assertIn("today_status=watchlist_blocked", html)
        self.assertIn("GLD", html)

    def test_load_priority_research_board_excludes_assets_without_real_chart(self) -> None:
        operator_row = pd.Series(
            {
                "model_name": "priority_line",
                "best_rule_name": "top_20pct_reference",
                "latest_score": 0.41,
                "recent_selected_count": 3,
                "latest_date": "2026-04-15",
                "latest_selected": False,
                "cutoff": 0.48,
                "days_since_last_selected": 8,
                "avg_return": 0.12,
                "selected_count": 11,
            }
        )

        with mock.patch.object(rmb.ac, "MONITOR_PRIORITY_RESEARCH_ASSET_KEYS", ("meta", "xlp")):
            with mock.patch.object(rmb, "_load_followup_rows", side_effect=[(operator_row, None, 4), (operator_row, None, 4)]):
                with mock.patch.object(rmb, "_load_snapshot_row", return_value=None):
                    with mock.patch.object(rmb, "load_display_latest_date", return_value="2026-04-15"):
                        with mock.patch.object(rmb.ac, "get_asset_symbol", side_effect=["META", "XLP"]):
                            with mock.patch.object(rmb, "has_real_chart", side_effect=[False, True]):
                                board = rmb.load_priority_research_board()

        self.assertEqual(list(board["asset_key"]), ["xlp"])
        self.assertEqual(list(board["chart_href"]), [rmb.ac.get_monitor_card_chart_path("xlp").relative_to(rmb.ac.REPO_DIR).as_posix()])

    def test_load_operating_board_excludes_assets_without_real_chart(self) -> None:
        snapshot = pd.DataFrame(
            [
                {
                    "asset_key": "gld",
                    "symbol": "GLD",
                    "preferred_line": "baseline_live",
                    "lane_type": "binary_operator",
                    "role": "primary",
                    "status": "active",
                    "action": "selected_now",
                    "recent_selected_count": 5,
                    "latest_date": "2026-04-15",
                    "latest_value": 0.51,
                    "latest_selected": True,
                    "cutoff": 0.48,
                    "last_selected_date": "2026-04-15",
                    "days_since_last_selected": 0,
                    "action_note": "ready",
                }
            ]
        )

        with mock.patch.object(rmb.ac, "MONITOR_BOARD_ASSET_KEYS", ("meta", "gld")):
            with mock.patch.object(rmb.ac, "get_monitor_snapshot_path", side_effect=[rmb.ac.REPO_DIR / "assets/meta/monitor_snapshot.tsv", rmb.ac.REPO_DIR / "assets/gld/monitor_snapshot.tsv"]):
                with mock.patch.object(pd, "read_csv", return_value=snapshot):
                    with mock.patch.object(rmb, "load_display_latest_date", return_value="2026-04-15"):
                        with mock.patch.object(rmb, "load_signal_color", return_value="#065f46"):
                            with mock.patch.object(rmb, "has_real_chart", side_effect=[False, True]):
                                board = rmb.load_operating_board()

        self.assertEqual(list(board["asset_key"]), ["gld"])

    def test_load_board_handles_empty_priority_research_after_chart_filtering(self) -> None:
        operating = pd.DataFrame(
            [
                {
                    "asset_key": "gld",
                    "symbol": "GLD",
                    "action": "selected_now",
                    "preferred_line": "baseline_live",
                }
            ]
        )
        empty_research = pd.DataFrame()

        with mock.patch.object(rmb, "load_operating_board", return_value=operating):
            with mock.patch.object(rmb, "load_priority_research_board", return_value=empty_research):
                board = rmb.load_board()

        self.assertEqual(list(board["asset_key"]), ["gld"])
        self.assertIn("research_score", board.columns)


if __name__ == "__main__":
    unittest.main()
