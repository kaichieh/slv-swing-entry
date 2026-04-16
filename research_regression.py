"""
Run a simple ridge-regression ranking study on future_return_60.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from typing import cast

import numpy as np
import pandas as pd

import asset_config as ac
import prepare as pr
import train as tr

OUTPUT_PATH = str(ac.get_regression_output_path())
DEFAULT_TOP_PCTS = (10.0, 15.0, 20.0)
DEFAULT_L2_REG = 1e-2


@dataclass
class BucketStat:
    split: str
    direction: str
    top_pct: float
    count: int
    avg_return: float
    hit_rate: float
    cutoff: float


def get_env_csv(name: str, default: tuple[str, ...] = ()) -> tuple[str, ...]:
    value = os.getenv(name)
    if value is None or not value.strip():
        return default
    return tuple(part.strip() for part in value.split(",") if part.strip())


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    return float(value) if value is not None else default


def get_top_pcts() -> tuple[float, ...]:
    raw = os.getenv("AR_REG_TOP_PCTS")
    if raw is None or not raw.strip():
        return DEFAULT_TOP_PCTS
    values: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        values.append(float(part))
    return tuple(values) if values else DEFAULT_TOP_PCTS


def load_raw_prices() -> pd.DataFrame:
    raw_path = ac.get_raw_data_path()
    if raw_path.exists():
        frame = cast(pd.DataFrame, pd.read_csv(raw_path))
        frame = cast(pd.DataFrame, frame[frame["date"].astype(str).str.contains("-")].copy())
        return pr.normalize_ohlcv_frame(frame)
    return pr.download_asset_prices()


def build_feature_names(frame: pd.DataFrame) -> list[str]:
    feature_names = list(pr.FEATURE_COLUMNS)
    for column in get_env_csv("AR_EXTRA_BASE_FEATURES"):
        if column in frame.columns and column not in feature_names:
            feature_names.append(column)
    drop_features = set(get_env_csv("AR_DROP_FEATURES"))
    return [name for name in feature_names if name not in drop_features]


def split_frame(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    train_end, valid_end = pr.split_indices(len(frame))
    return {
        "train": frame.iloc[:train_end].copy().reset_index(drop=True),
        "validation": frame.iloc[train_end:valid_end].copy().reset_index(drop=True),
        "test": frame.iloc[valid_end:].copy().reset_index(drop=True),
    }


def standardize(train_x: np.ndarray, other: list[np.ndarray]) -> tuple[np.ndarray, list[np.ndarray]]:
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return (train_x - mean) / std, [(matrix - mean) / std for matrix in other]


def fit_ridge_regression(train_x: np.ndarray, train_y: np.ndarray, l2_reg: float) -> np.ndarray:
    with_bias = np.concatenate([train_x, np.ones((train_x.shape[0], 1), dtype=train_x.dtype)], axis=1)
    identity = np.eye(with_bias.shape[1], dtype=with_bias.dtype)
    identity[-1, -1] = 0.0
    return np.linalg.solve(with_bias.T @ with_bias + l2_reg * identity, with_bias.T @ train_y)


def predict(matrix: np.ndarray, weights: np.ndarray) -> np.ndarray:
    with_bias = np.concatenate([matrix, np.ones((matrix.shape[0], 1), dtype=matrix.dtype)], axis=1)
    return with_bias @ weights


def safe_corr(left: np.ndarray, right: np.ndarray) -> float:
    if len(left) < 2 or np.std(left) < 1e-9 or np.std(right) < 1e-9:
        return 0.0
    return float(np.corrcoef(left, right)[0, 1])


def compute_bucket_stat(
    split: str, direction: str, predictions: np.ndarray, realized_returns: np.ndarray, top_pct: float
) -> BucketStat:
    if direction == "top":
        cutoff = float(np.quantile(predictions, 1.0 - top_pct / 100.0))
        selected = predictions >= cutoff
    elif direction == "bottom":
        cutoff = float(np.quantile(predictions, top_pct / 100.0))
        selected = predictions <= cutoff
    else:
        raise ValueError(f"Unsupported direction: {direction}")
    chosen = realized_returns[selected]
    return BucketStat(
        split=split,
        direction=direction,
        top_pct=top_pct,
        count=int(selected.sum()),
        avg_return=float(chosen.mean()) if len(chosen) else 0.0,
        hit_rate=float((chosen > 0).mean()) if len(chosen) else 0.0,
        cutoff=cutoff,
    )


def build_dataset() -> tuple[pd.DataFrame, list[str]]:
    raw = load_raw_prices()
    frame = pr.add_price_features(raw)
    frame = pr.add_relative_strength_features(frame, pr.BENCHMARK_SYMBOL)
    frame = pr.add_context_features(frame)
    frame = pr.add_vix_features(frame, pr.download_vix_prices())
    _labels, realized_returns = pr.build_barrier_labels(frame, 60, 0.08, -0.04)
    frame["future_return_60"] = realized_returns
    feature_names = build_feature_names(frame)
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(subset=feature_names + ["future_return_60"]).reset_index(drop=True)
    return frame, feature_names


def main() -> None:
    tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
    frame, feature_names = build_dataset()
    splits = split_frame(frame)
    train_x = splits["train"][feature_names].to_numpy(dtype=np.float64)
    valid_x = splits["validation"][feature_names].to_numpy(dtype=np.float64)
    test_x = splits["test"][feature_names].to_numpy(dtype=np.float64)
    train_y = splits["train"]["future_return_60"].to_numpy(dtype=np.float64)
    valid_y = splits["validation"]["future_return_60"].to_numpy(dtype=np.float64)
    test_y = splits["test"]["future_return_60"].to_numpy(dtype=np.float64)

    train_x, [valid_x, test_x] = standardize(train_x, [valid_x, test_x])
    weights = fit_ridge_regression(train_x, train_y, get_env_float("AR_REG_L2", DEFAULT_L2_REG))
    valid_pred = predict(valid_x, weights)
    test_pred = predict(test_x, weights)

    bucket_rows = []
    for split_name, predictions, realized_returns in (
        ("validation", valid_pred, valid_y),
        ("test", test_pred, test_y),
    ):
        for direction in ("top", "bottom"):
            for top_pct in get_top_pcts():
                bucket_rows.append(
                    asdict(compute_bucket_stat(split_name, direction, predictions, realized_returns, top_pct))
                )

    output = {
        "asset_key": ac.get_asset_key(),
        "symbol": ac.get_asset_symbol(),
        "feature_names": feature_names,
        "rows": len(frame),
        "validation_corr": safe_corr(valid_pred, valid_y),
        "test_corr": safe_corr(test_pred, test_y),
        "validation_avg_return": float(valid_y.mean()),
        "test_avg_return": float(test_y.mean()),
        "validation_positive_rate": float((valid_y > 0).mean()),
        "test_positive_rate": float((test_y > 0).mean()),
        "bucket_rows": bucket_rows,
    }

    pd.DataFrame(bucket_rows).to_csv(OUTPUT_PATH, sep="\t", index=False)
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
