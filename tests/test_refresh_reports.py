from __future__ import annotations

import unittest
from unittest import mock

import refresh_reports as rr


class RefreshReportsTests(unittest.TestCase):
    def test_refresh_asset_runs_standard_steps_for_non_mu(self) -> None:
        steps: list[tuple[str, str | None]] = []

        def fake_run_step(script_name: str, asset_key: str | None = None) -> None:
            steps.append((script_name, asset_key))

        with mock.patch.object(rr.ac, "uses_regression_chart", return_value=False):
            with mock.patch.object(rr, "run_step", side_effect=fake_run_step):
                rr.refresh_asset("gld")

        self.assertEqual(
            steps,
            [
                ("prepare.py", "gld"),
                ("chart_signals.py", "gld"),
                ("refresh_active_status.py", "gld"),
                ("render_active_status.py", "gld"),
                ("refresh_monitor_snapshot.py", "gld"),
                ("refresh_technical_reading.py", "gld"),
            ],
        )

    def test_refresh_asset_runs_mu_challenger_monitors_after_standard_steps(self) -> None:
        steps: list[tuple[str, str | None]] = []

        def fake_run_step(script_name: str, asset_key: str | None = None) -> None:
            steps.append((script_name, asset_key))

        with mock.patch.object(rr.ac, "uses_regression_chart", return_value=False):
            with mock.patch.object(rr, "run_step", side_effect=fake_run_step):
                rr.refresh_asset("mu")

        self.assertEqual(
            steps,
            [
                ("prepare.py", "mu"),
                ("chart_signals.py", "mu"),
                ("refresh_active_status.py", "mu"),
                ("render_active_status.py", "mu"),
                ("refresh_monitor_snapshot.py", "mu"),
                ("refresh_technical_reading.py", "mu"),
                ("refresh_mu_shadow_board.py", "mu"),
                ("refresh_mu_divergence_report.py", "mu"),
                ("refresh_mu_subregime_report.py", "mu"),
                ("refresh_mu_live_bucket_report.py", "mu"),
                ("refresh_mu_tolerance_report.py", "mu"),
                ("refresh_mu_gap_volume_ignition_v82_reports.py", "mu"),
            ],
        )

    def test_run_mu_challenger_monitors_uses_mu_asset_env(self) -> None:
        with mock.patch.object(rr, "run_step") as run_step:
            rr.run_mu_challenger_monitors()

        self.assertEqual(
            run_step.call_args_list,
            [
                mock.call("refresh_mu_shadow_board.py", "mu"),
                mock.call("refresh_mu_divergence_report.py", "mu"),
                mock.call("refresh_mu_subregime_report.py", "mu"),
                mock.call("refresh_mu_live_bucket_report.py", "mu"),
                mock.call("refresh_mu_tolerance_report.py", "mu"),
                mock.call("refresh_mu_gap_volume_ignition_v82_reports.py", "mu"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
