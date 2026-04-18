from __future__ import annotations

import pandas as pd

import refresh_mu_divergence_report as report


def test_classify_outcome_bucket_distinguishes_live_and_shadow_selection() -> None:
    live_selected = pd.Series({"live_state": "selected", "shadow_state": "idle"})
    shadow_selected = pd.Series({"live_state": "blocked", "shadow_state": "selected"})
    both_blocked = pd.Series({"live_state": "blocked", "shadow_state": "blocked"})

    assert report.classify_outcome_bucket(live_selected) == "live_selected_while_shadow_not"
    assert report.classify_outcome_bucket(shadow_selected) == "shadow_selected_while_live_not"
    assert report.classify_outcome_bucket(both_blocked) == "both_blocked"


def test_bucket_promotion_verdict_flips_when_owner_bucket_underperforms() -> None:
    assert report.bucket_promotion_verdict("live", 5, 0.10, 0.60) == "supports_live"
    assert report.bucket_promotion_verdict("live", 5, -0.02, 0.40) == "supports_challenger"
    assert report.bucket_promotion_verdict("challenger", 5, 0.08, 0.55) == "supports_challenger"
    assert report.bucket_promotion_verdict("challenger", 5, -0.01, 0.45) == "supports_live"
    assert report.bucket_promotion_verdict("shared", 10, 0.12, 0.70) == "inconclusive"


def test_build_summary_frame_computes_matured_counts_and_bullish_pocket_counts() -> None:
    frame = pd.DataFrame(
        [
            {
                "outcome_bucket": "shadow_selected_while_live_not",
                "live_confidence_gap": -0.01,
                "shadow_confidence_gap": 0.02,
                "confidence_gap_delta": 0.03,
                "matured_20d": True,
                "future_return_20d": 0.10,
                "matured_60d": True,
                "future_return_60d": 0.25,
                "bullish_pocket": True,
                "bullish_pocket_confirmed": True,
            },
            {
                "outcome_bucket": "shadow_selected_while_live_not",
                "live_confidence_gap": -0.02,
                "shadow_confidence_gap": 0.01,
                "confidence_gap_delta": 0.03,
                "matured_20d": False,
                "future_return_20d": None,
                "matured_60d": False,
                "future_return_60d": None,
                "bullish_pocket": False,
                "bullish_pocket_confirmed": False,
            },
            {
                "outcome_bucket": "both_selected",
                "live_confidence_gap": 0.08,
                "shadow_confidence_gap": 0.04,
                "confidence_gap_delta": -0.04,
                "matured_20d": True,
                "future_return_20d": 0.15,
                "matured_60d": True,
                "future_return_60d": 0.30,
                "bullish_pocket": True,
                "bullish_pocket_confirmed": False,
            },
        ]
    )

    summary = report.build_summary_frame(frame)

    shadow_row = summary.loc[summary["outcome_bucket"] == "shadow_selected_while_live_not"].iloc[0]
    assert shadow_row["row_count"] == 2
    assert shadow_row["matured_20d_count"] == 1
    assert shadow_row["avg_return_20d"] == 0.1
    assert shadow_row["hit_rate_20d"] == 1.0
    assert shadow_row["bullish_pocket_count"] == 1


def test_rollup_prefers_live_when_live_owned_buckets_are_stronger() -> None:
    frame = pd.DataFrame(
        [
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.35,
                "bullish_pocket": True,
                "date": "2026-01-01",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.20,
                "bullish_pocket": False,
                "date": "2026-01-02",
            },
            {
                "promotion_bucket": "shadow_selected_live_idle",
                "comparison_owner": "challenger",
                "matured_60d": True,
                "future_return_60d": 0.05,
                "bullish_pocket": True,
                "date": "2026-01-03",
            },
            {
                "promotion_bucket": "shadow_selected_live_idle",
                "comparison_owner": "challenger",
                "matured_60d": True,
                "future_return_60d": -0.10,
                "bullish_pocket": False,
                "date": "2026-01-04",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.18,
                "bullish_pocket": True,
                "date": "2026-01-05",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.22,
                "bullish_pocket": True,
                "date": "2026-01-06",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.19,
                "bullish_pocket": True,
                "date": "2026-01-07",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.16,
                "bullish_pocket": False,
                "date": "2026-01-08",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.21,
                "bullish_pocket": False,
                "date": "2026-01-09",
            },
            {
                "promotion_bucket": "live_selected_shadow_idle",
                "comparison_owner": "live",
                "matured_60d": True,
                "future_return_60d": 0.17,
                "bullish_pocket": True,
                "date": "2026-01-10",
            },
        ]
    )

    summary = report.build_bucket_summary(frame)
    rollup = report.build_rollup_row(summary)
    assert rollup["promotion_verdict"] == "supports_live"
