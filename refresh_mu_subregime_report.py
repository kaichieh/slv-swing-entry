from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import prepare as pr
import refresh_mu_divergence_report as report

ASSET_KEY = report.ASSET_KEY

CASE_ORDER = (
    "live_blocked_shadow_selected",
    "shadow_selected_live_idle",
    "live_selected_shadow_idle",
    "shadow_blocked_live_selected",
    "both_selected",
    "both_idle",
)
REGIME_ORDER = (
    "all_shared",
    "above_200dma_bullish_pocket",
    "above_200dma_and_slope_60_positive",
    "bullish_pullback_dd20_le_-0.03",
)


def get_output_dir() -> Path:
    return report.get_output_dir()


def get_summary_path() -> Path:
    return get_output_dir() / "subregime_divergence_summary.tsv"


def get_compare_path() -> Path:
    return get_output_dir() / "subregime_divergence_compare.tsv"


def get_cases_path() -> Path:
    return get_output_dir() / "subregime_divergence_cases.tsv"


def load_subregime_frame() -> pd.DataFrame:
    compare = report.load_compare_frame()
    prices = report.normalize_price_frame(pr.download_asset_prices())
    frame = report.attach_outcomes(compare, prices)
    if frame.empty:
        raise ValueError("MU subregime frame is empty.")
    return frame


def summarize_returns(values: pd.Series) -> dict[str, float | int]:
    clean = values.dropna().astype(float)
    if clean.empty:
        return {
            "count": 0,
            "avg_future_return_60": 0.0,
            "median_future_return_60": 0.0,
            "hit_rate": 0.0,
            "avg_future_return_60_ex_best": 0.0,
            "max_future_return_60": 0.0,
        }
    array = clean.to_numpy(dtype=np.float64)
    if len(array) > 1:
        drop_best = np.delete(array, int(np.argmax(array)))
        avg_ex_best = float(drop_best.mean())
    else:
        avg_ex_best = float(array.mean())
    return {
        "count": int(len(array)),
        "avg_future_return_60": float(array.mean()),
        "median_future_return_60": float(np.median(array)),
        "hit_rate": float((array > 0).mean()),
        "avg_future_return_60_ex_best": avg_ex_best,
        "max_future_return_60": float(array.max()),
    }


def assess_challenger_case(
    challenger: dict[str, float | int],
    live_only: dict[str, float | int],
    both_idle: dict[str, float | int],
) -> tuple[str, str]:
    challenger_count = int(challenger["count"])
    challenger_hit = float(challenger["hit_rate"])
    challenger_avg = float(challenger["avg_future_return_60"])
    challenger_avg_ex_best = float(challenger["avg_future_return_60_ex_best"])
    live_count = int(live_only["count"])
    live_avg = float(live_only["avg_future_return_60"])
    live_hit = float(live_only["hit_rate"])
    idle_avg = float(both_idle["avg_future_return_60"])

    if challenger_count < 10:
        return "too_thin", "Sample is too small to treat as an actionable challenger pocket."
    if challenger_hit < 0.6:
        return "not_clean_enough", "Challenger disagreement hit rate stays below 60% even inside the favorable slice."
    if challenger_avg_ex_best <= idle_avg:
        return "outlier_sensitive", "Removing the best case leaves the challenger close to or below the both-idle baseline."
    if live_count and challenger_avg <= live_avg and challenger_hit <= live_hit:
        return "still_weaker_than_live", "Challenger disagreement still does not beat the rare live-only selections."
    return "followup_candidate", "Slice is strong enough to justify another targeted follow-up."


def build_regime_masks(frame: pd.DataFrame) -> dict[str, pd.Series]:
    bullish_pocket = frame["bullish_pocket"].fillna(False).astype(bool)
    bullish_pocket_confirmed = frame["bullish_pocket_confirmed"].fillna(False).astype(bool)
    return {
        "all_shared": pd.Series(True, index=frame.index),
        "above_200dma_bullish_pocket": bullish_pocket,
        "above_200dma_and_slope_60_positive": bullish_pocket_confirmed,
        "bullish_pullback_dd20_le_-0.03": bullish_pocket_confirmed & (frame["drawdown_20"].fillna(0.0) <= -0.03),
    }


def build_summary_frame(frame: pd.DataFrame) -> pd.DataFrame:
    regime_masks = build_regime_masks(frame)
    rows: list[dict[str, object]] = []
    for regime_name in REGIME_ORDER:
        regime_frame = frame.loc[regime_masks[regime_name]].copy()
        for bucket in CASE_ORDER:
            bucket_returns = regime_frame.loc[regime_frame["promotion_bucket"] == bucket, "future_return_60d"]
            metrics = summarize_returns(bucket_returns)
            rows.append(
                {
                    "regime": regime_name,
                    "sample_rows": int(len(regime_frame)),
                    "promotion_bucket": bucket,
                    **metrics,
                }
            )
    return pd.DataFrame(rows)


def build_compare_frame(summary: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    challenger_buckets = ("live_blocked_shadow_selected", "shadow_selected_live_idle")
    live_buckets = ("live_selected_shadow_idle", "shadow_blocked_live_selected")
    for regime_name in REGIME_ORDER:
        subset = summary.loc[summary["regime"] == regime_name].copy()
        by_bucket = {
            bucket: subset.loc[subset["promotion_bucket"] == bucket].iloc[0].to_dict() for bucket in CASE_ORDER
        }
        challenger_count = sum(int(by_bucket[bucket]["count"]) for bucket in challenger_buckets)
        live_only_count = sum(int(by_bucket[bucket]["count"]) for bucket in live_buckets)
        challenger_avg = (
            float(
                np.average(
                    [float(by_bucket[bucket]["avg_future_return_60"]) for bucket in challenger_buckets],
                    weights=[max(int(by_bucket[bucket]["count"]), 0) for bucket in challenger_buckets],
                )
            )
            if challenger_count
            else 0.0
        )
        challenger_hit = (
            float(
                np.average(
                    [float(by_bucket[bucket]["hit_rate"]) for bucket in challenger_buckets],
                    weights=[max(int(by_bucket[bucket]["count"]), 0) for bucket in challenger_buckets],
                )
            )
            if challenger_count
            else 0.0
        )
        challenger_avg_ex_best = (
            float(
                np.average(
                    [float(by_bucket[bucket]["avg_future_return_60_ex_best"]) for bucket in challenger_buckets],
                    weights=[max(int(by_bucket[bucket]["count"]), 0) for bucket in challenger_buckets],
                )
            )
            if challenger_count
            else 0.0
        )
        live_only_avg = (
            float(
                np.average(
                    [float(by_bucket[bucket]["avg_future_return_60"]) for bucket in live_buckets],
                    weights=[max(int(by_bucket[bucket]["count"]), 0) for bucket in live_buckets],
                )
            )
            if live_only_count
            else 0.0
        )
        live_only_hit = (
            float(
                np.average(
                    [float(by_bucket[bucket]["hit_rate"]) for bucket in live_buckets],
                    weights=[max(int(by_bucket[bucket]["count"]), 0) for bucket in live_buckets],
                )
            )
            if live_only_count
            else 0.0
        )
        challenger_metrics = {
            "count": challenger_count,
            "avg_future_return_60": challenger_avg,
            "hit_rate": challenger_hit,
            "avg_future_return_60_ex_best": challenger_avg_ex_best,
        }
        live_metrics = {
            "count": live_only_count,
            "avg_future_return_60": live_only_avg,
            "hit_rate": live_only_hit,
        }
        both_idle_metrics = by_bucket["both_idle"]
        verdict, note = assess_challenger_case(challenger_metrics, live_metrics, both_idle_metrics)
        rows.append(
            {
                "regime": regime_name,
                "sample_rows": int(subset["sample_rows"].iloc[0]),
                "challenger_only_count": challenger_count,
                "challenger_only_avg_future_return_60": round(challenger_avg, 4),
                "challenger_only_hit_rate": round(challenger_hit, 4),
                "challenger_only_avg_future_return_60_ex_best": round(challenger_avg_ex_best, 4),
                "live_only_count": live_only_count,
                "live_only_avg_future_return_60": round(live_only_avg, 4),
                "live_only_hit_rate": round(live_only_hit, 4),
                "both_selected_count": int(by_bucket["both_selected"]["count"]),
                "both_selected_avg_future_return_60": round(float(by_bucket["both_selected"]["avg_future_return_60"]), 4),
                "both_selected_hit_rate": round(float(by_bucket["both_selected"]["hit_rate"]), 4),
                "both_idle_count": int(by_bucket["both_idle"]["count"]),
                "both_idle_avg_future_return_60": round(float(by_bucket["both_idle"]["avg_future_return_60"]), 4),
                "both_idle_hit_rate": round(float(by_bucket["both_idle"]["hit_rate"]), 4),
                "challenger_vs_live_avg_gap": round(challenger_avg - live_only_avg, 4),
                "challenger_vs_both_idle_avg_gap": round(challenger_avg - float(both_idle_metrics["avg_future_return_60"]), 4),
                "challenger_verdict": verdict,
                "challenger_note": note,
            }
        )
    return pd.DataFrame(rows)


def build_cases_frame(frame: pd.DataFrame) -> pd.DataFrame:
    cases = frame.loc[frame["promotion_bucket"].isin(CASE_ORDER[:-1])].copy()
    if cases.empty:
        return cases
    columns = [
        "date",
        "promotion_bucket",
        "comparison_owner",
        "bullish_pocket",
        "bullish_pocket_confirmed",
        "bullish_pocket_label",
        "above_200dma_flag",
        "slope_60",
        "drawdown_20",
        "live_probability",
        "shadow_probability",
        "confidence_gap_delta",
        "future_return_20d",
        "future_return_60d",
    ]
    return cases[columns].sort_values("date").reset_index(drop=True)


def main() -> None:
    frame = load_subregime_frame()
    summary = build_summary_frame(frame)
    compare = build_compare_frame(summary)
    cases = build_cases_frame(frame)

    summary.to_csv(get_summary_path(), sep="\t", index=False)
    compare.to_csv(get_compare_path(), sep="\t", index=False)
    cases.to_csv(get_cases_path(), sep="\t", index=False)

    focus = compare.loc[compare["regime"] == "above_200dma_bullish_pocket"].iloc[0]
    print(
        json.dumps(
            {
                "asset_key": ASSET_KEY,
                "summary_path": str(get_summary_path()),
                "compare_path": str(get_compare_path()),
                "cases_path": str(get_cases_path()),
                "bullish_pocket_verdict": str(focus["challenger_verdict"]),
                "bullish_pocket_note": str(focus["challenger_note"]),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
