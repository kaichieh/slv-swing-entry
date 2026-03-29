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
import train as tr

OUTPUT_PATH = str(ac.get_regression_recent_output_path())
DEFAULT_LOOKBACK = 60
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

    train_x = splits["train"][feature_names].to_numpy(dtype=np.float64)
    validation_x = splits["validation"][feature_names].to_numpy(dtype=np.float64)
    test_x = splits["test"][feature_names].to_numpy(dtype=np.float64)
    train_y = splits["train"]["future_return_60"].to_numpy(dtype=np.float64)

    train_x, [validation_x, test_x] = rr.standardize(train_x, [validation_x, test_x])
    weights = rr.fit_ridge_regression(train_x, train_y, get_env_float("AR_REG_L2", rr.DEFAULT_L2_REG))

    validation_pred = rr.predict(validation_x, weights)
    test_pred = rr.predict(test_x, weights)
    history_pred = np.concatenate([validation_pred, test_pred])

    lookback = get_env_int("AR_REG_LOOKBACK", DEFAULT_LOOKBACK)
    direction = get_env_str("AR_REG_DIRECTION", DEFAULT_DIRECTION).lower()
    bucket_pct = get_env_float("AR_REG_BUCKET_PCT", DEFAULT_BUCKET_PCT)

    test_frame = splits["test"].copy()
    test_frame["predicted_return"] = test_pred
    if direction == "bottom":
        cutoff = float(np.quantile(history_pred, bucket_pct / 100.0))
        selected = test_frame["predicted_return"] <= cutoff
        percentile = (history_pred[:, None] <= test_frame["predicted_return"].to_numpy()[None, :]).mean(axis=0)
    else:
        cutoff = float(np.quantile(history_pred, 1.0 - bucket_pct / 100.0))
        selected = test_frame["predicted_return"] >= cutoff
        percentile = (history_pred[:, None] <= test_frame["predicted_return"].to_numpy()[None, :]).mean(axis=0)

    test_frame["bucket_direction"] = direction
    test_frame["bucket_pct"] = bucket_pct
    test_frame["bucket_cutoff"] = cutoff
    test_frame["selected"] = selected.to_numpy(dtype=bool)
    test_frame["prediction_percentile"] = percentile

    output = test_frame[
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
