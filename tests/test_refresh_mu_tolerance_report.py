from __future__ import annotations

import pandas as pd

import refresh_mu_tolerance_report as report


def test_apply_non_overlap_uses_horizon_spacing() -> None:
    frame = pd.DataFrame(
        {
            "future_return_60": [0.1, 0.2, -0.1, 0.3],
            "selected": [True, True, False, True],
        }
    )

    keep = report.apply_non_overlap(frame, "selected")

    assert keep.tolist() == [True, False, False, False]


def test_compute_strategy_stats_handles_empty_episode_set() -> None:
    frame = pd.DataFrame(
        {
            "future_return_60": [0.1, -0.2],
            "candidate": [False, False],
        }
    )

    stats = report.compute_strategy_stats(frame, "candidate")

    assert stats["selected_rows"] == 0.0
    assert stats["episode_count"] == 0.0
    assert stats["episode_avg_return"] == 0.0


def test_summarize_variant_marks_probe_as_monitoring_only() -> None:
    frame = pd.DataFrame(
        {
            "future_return_60": [0.2, -0.1, 0.15],
            "live_selected": [True, False, False],
            "shadow_selected_base": [False, False, False],
            "shadow_selected_shadow_tol_0_001": [True, False, True],
            "pocket": [True, True, False],
            "shadow_gap": [-0.0005, -0.002, -0.003],
        }
    )

    summary = report.summarize_variant("shadow_tol_0_001", frame, [frame.copy()], 0.001)

    assert summary["monitoring_scope"] == "side_probe_only"
    assert summary["full_oos_recovered_cases"] == 1
    assert summary["full_oos_recovery_share"] == 1.0
