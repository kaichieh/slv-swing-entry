from __future__ import annotations

import pandas as pd

import refresh_mu_live_bucket_report as report


def test_collect_non_overlap_episodes_respects_min_gap_days() -> None:
    frame = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-20", "2026-03-15", "2026-05-20"]),
            "future_return_60": [0.10, 0.20, 0.30, 0.40],
        }
    )

    episodes = report.collect_non_overlap_episodes(frame, min_gap_days=60)

    assert episodes["date"].dt.strftime("%Y-%m-%d").tolist() == ["2026-01-01", "2026-03-15", "2026-05-20"]


def test_summarize_bucket_marks_monitor_as_hold_anchor() -> None:
    compare = pd.DataFrame({"date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"])})
    bucket = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-04-01"]),
            "future_return_20": [0.10, 0.05],
            "future_return_60": [0.25, 0.15],
            "above_200dma": [True, False],
            "slope_60_positive": [True, True],
            "shadow_gap": [-0.002, -0.004],
        }
    )

    summary = report.summarize_bucket(compare, bucket)
    summary_map = dict(zip(summary["metric"], summary["value"]))

    assert summary_map["monitor_verdict"] == "hold_anchor_watch"
    assert summary_map["bucket_rows"] == 2
    assert summary_map["bucket_non_overlap_60d_episodes"] == 2
    assert summary_map["future_return_60_hit_rate"] == 1.0


def test_build_recent_frame_keeps_most_recent_rows_and_core_columns() -> None:
    bucket = pd.DataFrame(
        {
            "date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "close": [100.0, 101.0],
            "future_return_20": [0.10, 0.20],
            "future_return_60": [0.25, 0.30],
            "live_probability": [0.61, 0.62],
            "live_cutoff": [0.50, 0.50],
            "live_gap": [0.11, 0.12],
            "live_signal": ["strong_bullish", "strong_bullish"],
            "shadow_probability": [0.49, 0.495],
            "shadow_cutoff": [0.50, 0.50],
            "shadow_gap": [-0.01, -0.005],
            "shadow_signal": ["no_entry", "no_entry"],
            "gap_spread": [0.12, 0.125],
            "above_200dma": [True, True],
            "slope_60_positive": [True, True],
            "bullish_pocket_label": ["above_200dma_and_slope_60_positive", "above_200dma_and_slope_60_positive"],
            "ret_60": [0.3, 0.31],
            "distance_from_60d_low": [0.2, 0.22],
            "vol_ratio_20_120": [1.1, 1.2],
        }
    )

    recent = report.build_recent_frame(bucket)

    assert recent["date"].tolist() == ["2026-01-01", "2026-01-02"]
    assert "bullish_pocket_label" in recent.columns
    assert "shadow_gap" in recent.columns
