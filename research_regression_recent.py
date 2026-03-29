"""
Export recent ridge-regression ranking scores for the active asset.
"""

from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

import asset_config as ac
import research_regression as rr
import prepare as pr
import train as tr

OUTPUT_PATH = str(ac.get_regression_recent_output_path())
DEFAULT_LOOKBACK = 5 * 252
DEFAULT_DIRECTION = "bottom"
DEFAULT_BUCKET_PCT = 15.0


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value is not None and value.strip() else default


def main() -> None:
    tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
    frame, feature_names = rr.build_dataset()
    splits = rr.split_frame(frame)

    live_raw = rr.load_raw_prices()
    live_frame = pr.add_price_features(live_raw)
    live_frame = pr.add_relative_strength_features(live_frame, pr.BENCHMARK_SYMBOL)
    live_frame = pr.add_context_features(live_frame)
    _live_labels, live_realized_returns = pr.build_barrier_labels(live_frame, 60, 0.08, -0.04)
    live_frame["future_return_60"] = live_realized_returns
    live_frame = live_frame.replace([np.inf, -np.inf], np.nan)
    live_frame = live_frame.dropna(subset=feature_names).reset_index(drop=True)

    train_x = splits["train"][feature_names].to_numpy(dtype=np.float64)
    validation_x = splits["validation"][feature_names].to_numpy(dtype=np.float64)
    test_x = splits["test"][feature_names].to_numpy(dtype=np.float64)
    live_x = live_frame[feature_names].to_numpy(dtype=np.float64)
    train_y = splits["train"]["future_return_60"].to_numpy(dtype=np.float64)

    train_x, [validation_x, test_x, live_x] = rr.standardize(train_x, [validation_x, test_x, live_x])
    weights = rr.fit_ridge_regression(train_x, train_y, get_env_float("AR_REG_L2", rr.DEFAULT_L2_REG))

    validation_pred = rr.predict(validation_x, weights)
    test_pred = rr.predict(test_x, weights)
    live_pred = rr.predict(live_x, weights)
    history_pred = np.concatenate([validation_pred, test_pred])

    lookback = get_env_int("AR_REG_LOOKBACK", DEFAULT_LOOKBACK)
    direction = get_env_str("AR_REG_DIRECTION", DEFAULT_DIRECTION).lower()
    bucket_pct = get_env_float("AR_REG_BUCKET_PCT", DEFAULT_BUCKET_PCT)

    recent_frame = live_frame.copy()
    recent_frame["predicted_return"] = live_pred
    if direction == "bottom":
        cutoff = float(np.quantile(history_pred, bucket_pct / 100.0))
        selected = recent_frame["predicted_return"] <= cutoff
        percentile = (history_pred[:, None] <= recent_frame["predicted_return"].to_numpy()[None, :]).mean(axis=0)
    else:
        cutoff = float(np.quantile(history_pred, 1.0 - bucket_pct / 100.0))
        selected = recent_frame["predicted_return"] >= cutoff
        percentile = (history_pred[:, None] <= recent_frame["predicted_return"].to_numpy()[None, :]).mean(axis=0)

    recent_frame["bucket_direction"] = direction
    recent_frame["bucket_pct"] = bucket_pct
    recent_frame["bucket_cutoff"] = cutoff
    recent_frame["selected"] = selected.to_numpy(dtype=bool)
    recent_frame["prediction_percentile"] = percentile

    output = recent_frame[
        [
            "date",
            "close",
            "predicted_return",
            "future_return_60",
            "prediction_percentile",
            "bucket_direction",
            "bucket_pct",
            "bucket_cutoff",
            "selected",
        ]
    ].tail(lookback)
    output.to_csv(OUTPUT_PATH, sep="\t", index=False)

    summary = {
        "asset_key": ac.get_asset_key(),
        "feature_names": feature_names,
        "direction": direction,
        "bucket_pct": bucket_pct,
        "bucket_cutoff": cutoff,
        "lookback_rows": len(output),
        "latest_date": output["date"].iloc[-1].strftime("%Y-%m-%d") if len(output) else None,
        "latest_predicted_return": float(output["predicted_return"].iloc[-1]) if len(output) else None,
        "latest_selected": bool(output["selected"].iloc[-1]) if len(output) else False,
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
