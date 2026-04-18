from __future__ import annotations

import pandas as pd

import refresh_mu_shadow_board as shadow


def test_classify_divergence_case_flags_live_blocked_shadow_selected() -> None:
    row = pd.Series(
        {
            "live_selected": False,
            "shadow_selected": True,
            "live_blocked": True,
            "shadow_blocked": False,
            "live_model_ready": True,
            "shadow_model_ready": True,
        }
    )

    assert shadow.classify_divergence_case(row) == "live_blocked_shadow_selected"


def test_classify_comparison_owner_maps_directional_cases() -> None:
    assert shadow.classify_comparison_owner("live_selected_shadow_idle") == "live"
    assert shadow.classify_comparison_owner("shadow_blocked_live_selected") == "live"
    assert shadow.classify_comparison_owner("live_blocked_shadow_selected") == "challenger"
    assert shadow.classify_comparison_owner("both_selected") == "shared"


def test_build_diff_frame_filters_non_divergent_rows() -> None:
    frame = pd.DataFrame(
        [
            {
                "date": "2026-04-16",
                "divergence_case": "",
                "live_signal": "no_entry",
                "live_raw_model_signal": "no_entry",
                "live_probability": 0.4,
                "live_cutoff": 0.5,
                "live_confidence_gap": -0.1,
                "shadow_signal": "no_entry",
                "shadow_raw_model_signal": "no_entry",
                "shadow_probability": 0.42,
                "shadow_cutoff": 0.5,
                "shadow_confidence_gap": -0.08,
                "confidence_gap_delta": 0.02,
            },
            {
                "date": "2026-04-17",
                "divergence_case": "shadow_selected_live_idle",
                "live_signal": "no_entry",
                "live_raw_model_signal": "no_entry",
                "live_probability": 0.45,
                "live_cutoff": 0.5,
                "live_confidence_gap": -0.05,
                "shadow_signal": "weak_bullish",
                "shadow_raw_model_signal": "weak_bullish",
                "shadow_probability": 0.52,
                "shadow_cutoff": 0.5,
                "shadow_confidence_gap": 0.02,
                "confidence_gap_delta": 0.07,
                "comparison_owner": "challenger",
                "bullish_pocket": True,
                "bullish_pocket_confirmed": True,
                "bullish_pocket_label": "above_200dma_and_slope_60_positive",
            },
        ]
    )

    diff = shadow.build_diff_frame(frame)

    assert list(diff["date"]) == ["2026-04-17"]
    assert list(diff["divergence_case"]) == ["shadow_selected_live_idle"]
    assert list(diff["bullish_pocket_label"]) == ["above_200dma_and_slope_60_positive"]
