from __future__ import annotations

import unittest

import pandas as pd

import refresh_monitor_board as rmb


class RefreshMonitorBoardTests(unittest.TestCase):
    def test_build_html_includes_watchlist_blocked_cards_in_today_section(self) -> None:
        board = pd.DataFrame(
            [
                {
                    "asset_key": "gld",
                    "symbol": "GLD",
                    "preferred_line": "hard_gate_two_expert_mixed_live",
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


if __name__ == "__main__":
    unittest.main()
