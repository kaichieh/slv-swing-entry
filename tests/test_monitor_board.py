import unittest

import pandas as pd

from refresh_monitor_board import build_html


class MonitorBoardTest(unittest.TestCase):
    def test_dashboard_html_shows_research_triage_sections(self):
        board = pd.DataFrame(
            [
                {
                    "symbol": "SLV",
                    "action": "research_only",
                    "preferred_line": "baseline_threshold",
                    "action_note": "Keep as research-only",
                    "chart_href": "assets/slv/regression_recent.html",
                    "latest_value": 0.44,
                    "cutoff": 0.38,
                    "last_selected_date": "2026-04-01",
                    "days_since_last_selected": 0,
                    "recent_selected_count": 12,
                    "display_latest_date": "2026-04-01",
                    "signal_color": "#64748b",
                    "role": "research_primary",
                    "research_lane": "macro_defensive_commodity",
                    "viability": "viable_with_caution",
                    "adoption_state": "keep_as_research_primary",
                }
            ]
        )

        html = build_html(board)

        self.assertIn("Research Triage", html)
        self.assertIn("viable_with_caution", html)
        self.assertIn("macro_defensive_commodity", html)


if __name__ == "__main__":
    unittest.main()
