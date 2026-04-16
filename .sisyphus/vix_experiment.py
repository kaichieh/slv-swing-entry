from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, cast


REPO_DIR = Path(__file__).resolve().parents[1]
VIX_CACHE_PATH = REPO_DIR / ".cache" / "vixcls.csv"
VIX_FEATURES = (
    "vix_close_lag1",
    "vix_change_1",
    "vix_change_5",
    "vix_z_20",
    "vix_percentile_20",
    "vix_high_regime_flag",
)
BOARD_BINARY_ASSETS = ("gld", "slv", "iwm", "spy", "nvda", "tsla")
BOARD_REGRESSION_ASSETS = ("qqq", "tlt", "xle")


def merged_extra_features(configured: list[str], include_vix: bool) -> str:
    values = list(dict.fromkeys([*configured, *(VIX_FEATURES if include_vix else ())]))
    return ",".join(values)


def run_worker(kind: str, asset: str, include_vix: bool) -> dict[str, Any]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_DIR)
    env["VIX_EXPERIMENT_ASSET"] = asset
    env["VIX_EXPERIMENT_KIND"] = kind
    env["VIX_EXPERIMENT_INCLUDE_VIX"] = "1" if include_vix else "0"
    command = [sys.executable, str(Path(__file__).resolve()), "--worker"]
    completed = subprocess.run(command, cwd=REPO_DIR, env=env, check=True, capture_output=True, text=True)
    return cast(dict[str, Any], json.loads(completed.stdout))


def probabilities_to_logits(probabilities):
    import numpy as np

    clipped = np.clip(probabilities, 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def binary_worker(asset: str, include_vix: bool) -> dict[str, object]:
    import asset_config as ac

    config = ac.load_asset_config(asset)
    configured_features = []
    live_extra = config.get("live_extra_features", [])
    if isinstance(live_extra, list):
        configured_features = [str(value) for value in live_extra]

    os.environ["AR_ASSET"] = asset
    os.environ["AR_LABEL_MODE"] = str(config.get("live_label_mode", config.get("label_mode", "drop-neutral")))
    os.environ["AR_EXTRA_BASE_FEATURES"] = merged_extra_features(configured_features, include_vix)

    import predict_latest as pl
    import prepare as pr
    import research_batch as rb
    import train as tr
    import pandas as pd

    if VIX_CACHE_PATH.exists():
        cached_vix = pr.normalize_vix_frame(pd.read_csv(VIX_CACHE_PATH))

        def load_cached_vix(url: str = pr.VIX_CSV_URL):
            _ = url
            return cached_vix.copy()

        def load_cached_vix_for_live():
            return cached_vix.copy()

        pr.download_vix_prices = load_cached_vix
        pl.download_vix_prices = load_cached_vix_for_live
        original_build_labeled_frame = rb.build_labeled_frame

        def build_labeled_frame_with_vix(
            raw,
            horizon_days: int = 60,
            upper_barrier: float = 0.08,
            lower_barrier: float = -0.04,
            label_mode: str = "drop-neutral",
        ):
            frame = original_build_labeled_frame(
                raw,
                horizon_days=horizon_days,
                upper_barrier=upper_barrier,
                lower_barrier=lower_barrier,
                label_mode=label_mode,
            )
            return pr.add_vix_features(frame, cached_vix)

        rb.build_labeled_frame = build_labeled_frame_with_vix

    raw = pr.download_asset_prices()
    processed = pr.add_features(raw)
    pr.save_processed_dataset(processed)
    splits = pr.load_splits()
    feature_names = pl.build_feature_names()
    artifacts = pl.fit_model(splits, feature_names, raw_prices=raw)
    feature_names = list(artifacts["feature_names"])
    threshold = float(artifacts["threshold"])
    train_frame = artifacts["train_frame"]
    top_pct = pl.get_rule_top_pct()
    rule_name = f"top_{top_pct:g}pct"

    split_results: dict[str, dict[str, object]] = {}
    for split_name in ("validation", "test"):
        split = splits[split_name]
        matrix, _snapshot = pl.score_latest_row(artifacts, feature_names, train_frame, split.frame)
        probabilities = pl.predict_probabilities(artifacts, matrix)
        metrics = tr.compute_metrics(
            probabilities_to_logits(probabilities),
            split.labels,
            split.frame["future_return_60"].to_numpy(dtype="float32"),
            threshold,
        )
        threshold_selected, threshold_cutoff = rb.classify_probs_by_rule(probabilities, threshold, "threshold")
        top_selected, top_cutoff = rb.classify_probs_by_rule(probabilities, threshold, rule_name)
        threshold_backtest = rb.run_non_overlap_backtest(
            cast(Any, split.frame["date"]),
            split.frame["future_return_60"].to_numpy(dtype="float64"),
            threshold_selected.astype(bool),
            pr.HORIZON_DAYS,
            float(threshold_cutoff),
        )
        top_backtest = rb.run_non_overlap_backtest(
            cast(Any, split.frame["date"]),
            split.frame["future_return_60"].to_numpy(dtype="float64"),
            top_selected.astype(bool),
            pr.HORIZON_DAYS,
            float(top_cutoff),
        )
        split_results[split_name] = {
            "f1": float(metrics.f1),
            "balanced_accuracy": float(metrics.balanced_accuracy),
            "positive_rate": float(metrics.positive_rate),
            "threshold_rule": {
                "selected_count": int(threshold_backtest.selected_count),
                "hit_rate": float(threshold_backtest.hit_rate),
                "avg_return": float(threshold_backtest.avg_return),
                "max_drawdown_simple": float(threshold_backtest.max_drawdown_simple),
            },
            "top_rule": {
                "rule_name": rule_name,
                "selected_count": int(top_backtest.selected_count),
                "hit_rate": float(top_backtest.hit_rate),
                "avg_return": float(top_backtest.avg_return),
                "max_drawdown_simple": float(top_backtest.max_drawdown_simple),
            },
        }

    return {
        "asset": asset,
        "kind": "binary",
        "include_vix": include_vix,
        "model_family": str(artifacts["model_family"]),
        "feature_names": feature_names,
        "split_results": split_results,
    }


def regression_worker(asset: str, include_vix: bool) -> dict[str, object]:
    import asset_config as ac

    os.environ["AR_ASSET"] = asset
    os.environ["AR_EXTRA_BASE_FEATURES"] = merged_extra_features([], include_vix)

    import research_regression as rr
    import research_regression_walkforward as rrw
    import prepare as pr
    import pandas as pd

    if VIX_CACHE_PATH.exists():
        cached_vix = pr.normalize_vix_frame(pd.read_csv(VIX_CACHE_PATH))

        def load_cached_vix(url: str = pr.VIX_CSV_URL):
            _ = url
            return cached_vix.copy()

        pr.download_vix_prices = load_cached_vix

    frame, feature_names = rr.build_dataset()
    splits = rr.split_frame(frame)
    train_x = splits["train"][feature_names].to_numpy(dtype=float)
    valid_x = splits["validation"][feature_names].to_numpy(dtype=float)
    test_x = splits["test"][feature_names].to_numpy(dtype=float)
    train_y = splits["train"]["future_return_60"].to_numpy(dtype=float)
    valid_y = splits["validation"]["future_return_60"].to_numpy(dtype=float)
    test_y = splits["test"]["future_return_60"].to_numpy(dtype=float)

    train_x, [valid_x, test_x] = rr.standardize(train_x, [valid_x, test_x])
    weights = rr.fit_ridge_regression(train_x, train_y, rr.DEFAULT_L2_REG)
    valid_pred = rr.predict(valid_x, weights)
    test_pred = rr.predict(test_x, weights)
    preferred_direction = "bottom"
    valid_bucket = rr.compute_bucket_stat("validation", preferred_direction, valid_pred, valid_y, 15.0)
    test_bucket = rr.compute_bucket_stat("test", preferred_direction, test_pred, test_y, 15.0)
    walkforward = []
    for row in rrw.walk_forward_splits(frame.dropna(subset=feature_names + ["future_return_60"]).reset_index(drop=True), 4):
        fold_name, train, validation, test = row
        fold_train_x = train[feature_names].to_numpy(dtype=float)
        fold_valid_x = validation[feature_names].to_numpy(dtype=float)
        fold_test_x = test[feature_names].to_numpy(dtype=float)
        fold_train_y = train["future_return_60"].to_numpy(dtype=float)
        fold_valid_y = validation["future_return_60"].to_numpy(dtype=float)
        fold_test_y = test["future_return_60"].to_numpy(dtype=float)
        fold_train_x, [fold_valid_x, fold_test_x] = rr.standardize(fold_train_x, [fold_valid_x, fold_test_x])
        fold_weights = rr.fit_ridge_regression(fold_train_x, fold_train_y, rr.DEFAULT_L2_REG)
        fold_valid_pred = rr.predict(fold_valid_x, fold_weights)
        fold_test_pred = rr.predict(fold_test_x, fold_weights)
        fold_valid_bucket = rr.compute_bucket_stat("validation", preferred_direction, fold_valid_pred, fold_valid_y, 10.0)
        fold_test_bucket = rr.compute_bucket_stat("test", preferred_direction, fold_test_pred, fold_test_y, 10.0)
        walkforward.append(
            {
                "fold": fold_name,
                "validation_corr": rr.safe_corr(fold_valid_pred, fold_valid_y),
                "test_corr": rr.safe_corr(fold_test_pred, fold_test_y),
                "validation_bucket_avg_return": fold_valid_bucket.avg_return,
                "test_bucket_avg_return": fold_test_bucket.avg_return,
                "test_bucket_hit_rate": fold_test_bucket.hit_rate,
            }
        )

    return {
        "asset": asset,
        "kind": "regression",
        "include_vix": include_vix,
        "feature_names": feature_names,
        "validation_corr": rr.safe_corr(valid_pred, valid_y),
        "test_corr": rr.safe_corr(test_pred, test_y),
        "validation_bottom15_avg_return": valid_bucket.avg_return,
        "test_bottom15_avg_return": test_bucket.avg_return,
        "test_bottom15_hit_rate": test_bucket.hit_rate,
        "walkforward": walkforward,
    }


def worker_main() -> None:
    asset = os.environ["VIX_EXPERIMENT_ASSET"]
    kind = os.environ["VIX_EXPERIMENT_KIND"]
    include_vix = os.environ["VIX_EXPERIMENT_INCLUDE_VIX"] == "1"
    payload = binary_worker(asset, include_vix) if kind == "binary" else regression_worker(asset, include_vix)
    print(json.dumps(payload))


def safe_delta(current: float, baseline: float) -> float:
    return current - baseline if all(math.isfinite(value) for value in (current, baseline)) else float("nan")


def aggregate_results() -> dict[str, object]:
    binary: list[dict[str, Any]] = []
    for asset in BOARD_BINARY_ASSETS:
        baseline = run_worker("binary", asset, include_vix=False)
        vix = run_worker("binary", asset, include_vix=True)
        baseline_split_results = cast(dict[str, Any], baseline["split_results"])
        vix_split_results = cast(dict[str, Any], vix["split_results"])
        baseline_test = cast(dict[str, Any], baseline_split_results["test"])
        vix_test = cast(dict[str, Any], vix_split_results["test"])
        baseline_top_rule = cast(dict[str, Any], baseline_test["top_rule"])
        vix_top_rule = cast(dict[str, Any], vix_test["top_rule"])
        vix_feature_names = cast(list[str], vix["feature_names"])
        binary.append(
            {
                "asset": asset,
                "model_family": str(vix["model_family"]),
                "baseline_test_top_avg_return": float(baseline_top_rule["avg_return"]),
                "vix_test_top_avg_return": float(vix_top_rule["avg_return"]),
                "delta_test_top_avg_return": safe_delta(float(vix_top_rule["avg_return"]), float(baseline_top_rule["avg_return"])),
                "baseline_test_top_hit_rate": float(baseline_top_rule["hit_rate"]),
                "vix_test_top_hit_rate": float(vix_top_rule["hit_rate"]),
                "delta_test_top_hit_rate": safe_delta(float(vix_top_rule["hit_rate"]), float(baseline_top_rule["hit_rate"])),
                "baseline_test_bal_acc": float(baseline_test["balanced_accuracy"]),
                "vix_test_bal_acc": float(vix_test["balanced_accuracy"]),
                "delta_test_bal_acc": safe_delta(float(vix_test["balanced_accuracy"]), float(baseline_test["balanced_accuracy"])),
                "vix_features_active": [name for name in vix_feature_names if name.startswith("vix_")],
            }
        )

    regression: list[dict[str, Any]] = []
    for asset in BOARD_REGRESSION_ASSETS:
        baseline = run_worker("regression", asset, include_vix=False)
        vix = run_worker("regression", asset, include_vix=True)
        baseline_walkforward = cast(list[dict[str, Any]], baseline["walkforward"])
        vix_walkforward = cast(list[dict[str, Any]], vix["walkforward"])
        baseline_walkforward_avg = sum(float(row["test_bucket_avg_return"]) for row in baseline_walkforward) / len(baseline_walkforward)
        vix_walkforward_avg = sum(float(row["test_bucket_avg_return"]) for row in vix_walkforward) / len(vix_walkforward)
        regression_feature_names = cast(list[str], vix["feature_names"])
        regression.append(
            {
                "asset": asset,
                "baseline_test_bottom15_avg_return": float(baseline["test_bottom15_avg_return"]),
                "vix_test_bottom15_avg_return": float(vix["test_bottom15_avg_return"]),
                "delta_test_bottom15_avg_return": safe_delta(float(vix["test_bottom15_avg_return"]), float(baseline["test_bottom15_avg_return"])),
                "baseline_test_bottom15_hit_rate": float(baseline["test_bottom15_hit_rate"]),
                "vix_test_bottom15_hit_rate": float(vix["test_bottom15_hit_rate"]),
                "delta_test_bottom15_hit_rate": safe_delta(float(vix["test_bottom15_hit_rate"]), float(baseline["test_bottom15_hit_rate"])),
                "baseline_walkforward_avg_test_bucket_return": baseline_walkforward_avg,
                "vix_walkforward_avg_test_bucket_return": vix_walkforward_avg,
                "delta_walkforward_avg_test_bucket_return": safe_delta(vix_walkforward_avg, baseline_walkforward_avg),
                "vix_features_active": [name for name in regression_feature_names if name.startswith("vix_")],
            }
        )

    return {"binary": binary, "regression": regression}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        worker_main()
        return
    print(json.dumps(aggregate_results(), indent=2))


if __name__ == "__main__":
    main()
