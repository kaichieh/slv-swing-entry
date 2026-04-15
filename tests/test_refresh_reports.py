from __future__ import annotations

import unittest
from unittest import mock

import refresh_reports as rr


class RefreshReportsTests(unittest.TestCase):
    def test_refresh_asset_renders_active_status_html_after_summary(self) -> None:
        steps: list[str] = []

        def fake_run_step(script_name: str, asset_key: str | None = None) -> None:
            steps.append(script_name)

        with mock.patch.object(rr.ac, "uses_regression_chart", return_value=False):
            with mock.patch.object(rr, "run_step", side_effect=fake_run_step):
                rr.refresh_asset("gld")

        self.assertEqual(
            steps,
            [
                "prepare.py",
                "predict_latest.py",
                "chart_signals.py",
                "refresh_active_status.py",
                "render_active_status.py",
                "refresh_monitor_snapshot.py",
            ],
        )


if __name__ == "__main__":
    unittest.main()
