"""
Run walk-forward checks for the active regression ranking candidate.
"""

from __future__ import annotations

import json
import os

import pandas as pd

import asset_config as ac
import research_regression as rr

OUTPUT_PATH = str(ac.get_regression_walkforward_output_path())
DEFAULT_DIRECTION = "bottom"
DEFAULT_BUCKET_PCT = 10.0
DEFAULT_FOLDS = 4


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def get_env_str(name: str, default: str) -> str:
    value = os.getenv(name)
    return value.strip() if value is not None and value.strip() else default


def walk_forward_splits(frame: pd.DataFrame, folds: int) -> list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    total = len(frame)
    fold_size = total // (folds + 2)
    rows: list[tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for fold_idx in range(folds):
        train_end = fold_size * (fold_idx + 2)
        validation_end = train_end + fold_size
        test_end = min(validation_end + fold_size, total)
        if test_end - validation_end < max(30, fold_size // 2):
            break
        rows.append(
            (
                f"fold_{fold_idx + 1}",
                frame.iloc[:train_end].copy().reset_index(drop=True),
                frame.iloc[train_end:validation_end].copy().reset_index(drop=True),
                frame.iloc[validation_end:test_end].copy().reset_index(drop=True),
            )
        )
    return rows


def main() -> None:
    frame, feature_names = rr.build_dataset()
    direction = get_env_str("AR_REG_DIRECTION", DEFAULT_DIRECTION).lower()
    bucket_pct = get_env_float("AR_REG_BUCKET_PCT", DEFAULT_BUCKET_PCT)
    folds = get_env_int("AR_REG_FOLDS", DEFAULT_FOLDS)

    clean = frame.dropna(subset=feature_names + ["future_return_60"]).reset_index(drop=True)
    rows: list[dict[str, object]] = []
    for fold_name, train, validation, test in walk_forward_splits(clean, folds):
        train_x = train[feature_names].to_numpy(dtype=float)
        validation_x = validation[feature_names].to_numpy(dtype=float)
        test_x = test[feature_names].to_numpy(dtype=float)
        train_y = train["future_return_60"].to_numpy(dtype=float)
        validation_y = validation["future_return_60"].to_numpy(dtype=float)
        test_y = test["future_return_60"].to_numpy(dtype=float)

        train_x, [validation_x, test_x] = rr.standardize(train_x, [validation_x, test_x])
        weights = rr.fit_ridge_regression(train_x, train_y, rr.DEFAULT_L2_REG)
        validation_pred = rr.predict(validation_x, weights)
        test_pred = rr.predict(test_x, weights)
        validation_stat = rr.compute_bucket_stat("validation", direction, validation_pred, validation_y, bucket_pct)
        test_stat = rr.compute_bucket_stat("test", direction, test_pred, test_y, bucket_pct)

        rows.append(
            {
                "fold": fold_name,
                "train_rows": len(train),
                "validation_rows": len(validation),
                "test_rows": len(test),
                "validation_corr": rr.safe_corr(validation_pred, validation_y),
                "test_corr": rr.safe_corr(test_pred, test_y),
                "validation_bucket_avg_return": validation_stat.avg_return,
                "validation_bucket_hit_rate": validation_stat.hit_rate,
                "test_bucket_avg_return": test_stat.avg_return,
                "test_bucket_hit_rate": test_stat.hit_rate,
                "validation_avg_return": float(validation_y.mean()),
                "test_avg_return": float(test_y.mean()),
                "direction": direction,
                "bucket_pct": bucket_pct,
            }
        )

    table = pd.DataFrame(rows)
    table.to_csv(OUTPUT_PATH, sep="\t", index=False)
    print(json.dumps(table.to_dict(orient="records"), indent=2))


if __name__ == "__main__":
    main()
