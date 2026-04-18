from __future__ import annotations

import pandas as pd

import refresh_mu_gap_volume_ignition_v82_shadow as shadow


def test_evaluate_rule_row_requires_all_v82_legs() -> None:
    selected = shadow.evaluate_rule_row(
        pd.Series(
            {
                "overnight_gap": 0.005,
                "volume_vs_20": 0.50,
                "range_z_20": 0.50,
                "intraday_return": 0.0,
                "breakout_20": 1.0,
            }
        )
    )
    rejected = shadow.evaluate_rule_row(
        pd.Series(
            {
                "overnight_gap": 0.007,
                "volume_vs_20": 0.62,
                "range_z_20": 0.49,
                "intraday_return": 0.01,
                "breakout_20": 1.0,
            }
        )
    )

    assert selected["selected"] is True
    assert selected["criteria_pass_count"] == 5
    assert rejected["selected"] is False
    assert rejected["criteria_pass_count"] == 4
    assert rejected["range_z_20_pass"] is False


def test_build_shadow_rows_from_feature_frame_uses_sidecar_rule_output() -> None:
    feature_frame = pd.DataFrame(
        [
            {
                "date": "2026-04-16",
                "close": 100.0,
                "overnight_gap": 0.006,
                "volume_vs_20": 0.7,
                "range_z_20": 0.8,
                "intraday_return": 0.02,
                "breakout_20": 1.0,
            },
            {
                "date": "2026-04-17",
                "close": 101.5,
                "overnight_gap": 0.004,
                "volume_vs_20": 0.7,
                "range_z_20": 0.8,
                "intraday_return": 0.02,
                "breakout_20": 1.0,
            },
        ]
    )

    rows, metadata = shadow.build_shadow_rows_from_feature_frame(feature_frame, lookback_days=None)

    assert list(rows["signal"]) == ["rule_match", "no_entry"]
    assert list(rows["criteria_pass_count"]) == [5, 4]
    assert list(rows["line_id"].unique()) == [shadow.SHADOW_LINE_ID]
    assert metadata["execution_rule"] == shadow.SHADOW_EXECUTION_RULE
    assert shadow.OUTPUT_DIRNAME in str(shadow.get_output_dir())
