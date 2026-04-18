from __future__ import annotations

import pandas as pd

import refresh_mu_gap_volume_ignition_v82_live_bucket_report as report


def test_summarize_bucket_reports_v82_near_miss_share() -> None:
    compare = pd.DataFrame(
        [
            {
                "date": "2026-01-10",
                "matured_20d": True,
                "matured_60d": True,
                "future_return_20d": 0.04,
                "future_return_60d": 0.10,
                "above_200dma": True,
                "slope_60_positive": True,
                "shadow_criteria_pass_count": 4,
                "shadow_criteria_pass_rate": 0.8,
            },
            {
                "date": "2026-04-01",
                "matured_20d": True,
                "matured_60d": True,
                "future_return_20d": -0.01,
                "future_return_60d": 0.02,
                "above_200dma": False,
                "slope_60_positive": True,
                "shadow_criteria_pass_count": 3,
                "shadow_criteria_pass_rate": 0.6,
            },
        ]
    )

    summary = report.summarize_bucket(compare, compare)
    summary_map = dict(zip(summary["metric"], summary["value"]))

    assert summary_map["bucket_rows"] == 2
    assert summary_map["matured_60_count"] == 2
    assert summary_map["v82_full_match_share"] == 0.0
    assert summary_map["v82_four_of_five_share"] == 0.5
    assert summary_map["v82_pass_rate_median"] == 0.7
