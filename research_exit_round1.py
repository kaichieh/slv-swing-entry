"""
Run the first exit-signal research round on pure asset features.

Exit label definition:
- 1 if -8% is hit before +4% within 60 trading days
- 0 if +4% is hit before -8% within 60 trading days
- neutral rows are dropped
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import asset_config as ac
import prepare as pr
import research_batch as rb

CACHE_DIR = str(ac.get_cache_dir())
ROUND_OUTPUT_PATH = str(ac.get_exit_round_path())

EXIT_HORIZON_DAYS = 60
EXIT_UPPER_BARRIER = 0.04
EXIT_LOWER_BARRIER = -0.08


def round_float(value: float) -> float:
    return round(float(value), 4)


def build_exit_frame(raw: pd.DataFrame) -> pd.DataFrame:
    df = pr.add_price_features(raw)
    df = pr.add_context_features(df)
    df = rb.add_regime_features(df)
    entry_like_labels, realized_returns = pr.build_barrier_labels(
        df,
        horizon_days=EXIT_HORIZON_DAYS,
        upper_barrier=EXIT_UPPER_BARRIER,
        lower_barrier=EXIT_LOWER_BARRIER,
    )
    exit_labels = np.where(np.isnan(entry_like_labels), np.nan, 1.0 - entry_like_labels)
    df[pr.TARGET_COLUMN] = exit_labels
    df[rb.FUTURE_RETURN_COLUMN] = realized_returns
    needed = pr.FEATURE_COLUMNS + pr.EXPERIMENTAL_FEATURE_COLUMNS + [pr.TARGET_COLUMN, rb.FUTURE_RETURN_COLUMN]
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.dropna(subset=needed).reset_index(drop=True)


def split_summary(frame: pd.DataFrame) -> list[dict[str, object]]:
    splits = rb.split_frame(frame)
    rows: list[dict[str, object]] = []
    for split_name, split_frame in splits.items():
        labels = split_frame[pr.TARGET_COLUMN].to_numpy(dtype=np.float64)
        returns = split_frame[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
        rows.append(
            {
                "split": split_name,
                "rows": int(len(split_frame)),
                "positive_rate": round_float(labels.mean()),
                "avg_future_return_60": round_float(np.nanmean(returns)),
                "date_start": split_frame["date"].iloc[0].strftime("%Y-%m-%d"),
                "date_end": split_frame["date"].iloc[-1].strftime("%Y-%m-%d"),
            }
        )
    return rows


def model_rows(frame: pd.DataFrame) -> list[dict[str, object]]:
    specs = {
        "exit_baseline": (),
        "exit_ret_60_plus_sma_gap_60": ("ret_60", "sma_gap_60"),
        "exit_ret_60_plus_sma_gap_60_plus_rolling_vol_60": ("ret_60", "sma_gap_60", "rolling_vol_60"),
    }
    rows: list[dict[str, object]] = []
    for name, features in specs.items():
        result, _artifacts = rb.train_model(frame, name, extra_features=features)
        headline_score = rb.compute_headline_score(
            result.validation_f1,
            result.validation_bal_acc,
            result.test_f1,
            result.test_bal_acc,
        )
        rows.append(
            {
                "model_name": name,
                "extra_features": ",".join(features) if features else "(baseline)",
                "validation_f1": round_float(result.validation_f1),
                "validation_accuracy": round_float(result.validation_accuracy),
                "validation_bal_acc": round_float(result.validation_bal_acc),
                "test_f1": round_float(result.test_f1),
                "test_accuracy": round_float(result.test_accuracy),
                "test_bal_acc": round_float(result.test_bal_acc),
                "headline_score": round_float(headline_score),
                "promotion_gate": "pass"
                if rb.passes_promotion_gate(result.validation_bal_acc, result.test_bal_acc)
                else "fail",
            }
        )
    return rows


def main() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)
    raw = pr.download_asset_prices()
    frame = build_exit_frame(raw)
    payload = {
        "label_definition": {
            "horizon_days": EXIT_HORIZON_DAYS,
            "exit_downside_barrier": EXIT_LOWER_BARRIER,
            "cancel_upside_barrier": EXIT_UPPER_BARRIER,
            "target_meaning": "1 means downside hits first, suggesting exit/risk-off",
        },
        "split_summary": split_summary(frame),
        "model_summary": model_rows(frame),
    }
    with open(ROUND_OUTPUT_PATH, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
