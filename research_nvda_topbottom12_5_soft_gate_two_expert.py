from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import asset_config as ac
import prepare as pr
import research_batch as rb
import train as tr

ASSET_KEY = "nvda"
HORIZON_DAYS = 40
UPPER_BARRIER = 0.15
LOWER_BARRIER = -0.08
LABEL_MODE = "future-return-top-bottom-12.5pct"
ALGORITHM = "soft_gate_two_expert"
LEFT_MODEL_FAMILY = "logistic"
RIGHT_MODEL_FAMILY = "regime_dual_logistic"
RIGHT_GATE_FEATURE = "above_200dma_flag"
SOFT_GATE_FEATURE = "vol_ratio_20_120"
SOFT_GATE_SLOPE = 8.0
SOFT_GATE_OFFSET_STD = 0.25
SOFT_THRESHOLD = 0.496
EXTRA_FEATURES = (
    "ret_60",
    "sma_gap_60",
    "atr_pct_20",
    "close_location_20",
    "ret_20_vs_benchmark",
    "ret_60_vs_benchmark",
    "price_ratio_benchmark_z_20",
    "price_ratio_benchmark_z_60",
    "rs_vs_benchmark_60",
)
DROP_FEATURES: tuple[str, ...] = ()


def probabilities_to_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float32), 1e-6, 1.0 - 1.0e-6)
    return np.log(clipped / (1.0 - clipped))


def sigmoid(values: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(values, dtype=np.float32), -60.0, 60.0)
    return 1.0 / (1.0 + np.exp(-clipped))


def blend_probabilities(
    split_frame: pr.pd.DataFrame,
    left_probabilities: np.ndarray,
    right_probabilities: np.ndarray,
    boundary: float,
) -> np.ndarray:
    gate_values = split_frame[SOFT_GATE_FEATURE].to_numpy(dtype=np.float32)
    scale = float(split_frame[SOFT_GATE_FEATURE].std())
    if scale < 1e-6:
        scale = 1.0
    weights = sigmoid(SOFT_GATE_SLOPE * ((gate_values - boundary) / scale))
    return (weights * np.asarray(left_probabilities, dtype=np.float32)) + (
        (1.0 - weights) * np.asarray(right_probabilities, dtype=np.float32)
    )


def evaluate_winning_algorithm() -> dict[str, float | str | bool | tuple[str, ...]]:
    symbol = ac.get_asset_symbol(ASSET_KEY)
    raw = pr.download_symbol_prices(symbol, ac.stooq_url(symbol), str(ac.get_raw_data_path(ASSET_KEY)))
    benchmark_symbol = str(ac.load_asset_config(ASSET_KEY).get("benchmark_symbol", "")).strip().upper()
    original_benchmark_symbol = pr.BENCHMARK_SYMBOL
    try:
        pr.BENCHMARK_SYMBOL = benchmark_symbol
        frame = rb.build_labeled_frame(
            raw,
            horizon_days=HORIZON_DAYS,
            upper_barrier=UPPER_BARRIER,
            lower_barrier=LOWER_BARRIER,
            label_mode=LABEL_MODE,
        )
    finally:
        pr.BENCHMARK_SYMBOL = original_benchmark_symbol
    _left_result, left_artifacts = rb.train_model(
        frame,
        "nvda_topbottom12_5_soft_gate_left",
        extra_features=EXTRA_FEATURES,
        drop_features=DROP_FEATURES,
        model_family=LEFT_MODEL_FAMILY,
    )
    _right_result, right_artifacts = rb.train_model(
        frame,
        "nvda_topbottom12_5_soft_gate_right",
        extra_features=EXTRA_FEATURES,
        drop_features=DROP_FEATURES,
        model_family=RIGHT_MODEL_FAMILY,
        gate_feature=RIGHT_GATE_FEATURE,
    )
    splits = rb.split_frame(frame)
    validation = splits["validation"].reset_index(drop=True)
    test = splits["test"].reset_index(drop=True)

    boundary = float(validation[SOFT_GATE_FEATURE].median() + (SOFT_GATE_OFFSET_STD * validation[SOFT_GATE_FEATURE].std()))
    validation_probabilities = blend_probabilities(
        validation,
        np.asarray(left_artifacts["validation_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["validation_probabilities"], dtype=np.float32),
        boundary,
    )
    test_probabilities = blend_probabilities(
        test,
        np.asarray(left_artifacts["test_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["test_probabilities"], dtype=np.float32),
        boundary,
    )

    validation_metrics = tr.compute_metrics(
        probabilities_to_logits(validation_probabilities),
        validation[pr.TARGET_COLUMN].to_numpy(dtype=np.float32),
        validation[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        SOFT_THRESHOLD,
    )
    test_metrics = tr.compute_metrics(
        probabilities_to_logits(test_probabilities),
        test[pr.TARGET_COLUMN].to_numpy(dtype=np.float32),
        test[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        SOFT_THRESHOLD,
    )
    return {
        "asset": ASSET_KEY,
        "symbol": symbol,
        "horizon_days": HORIZON_DAYS,
        "upper_barrier": round(UPPER_BARRIER, 4),
        "lower_barrier": round(LOWER_BARRIER, 4),
        "label_mode": LABEL_MODE,
        "algorithm": ALGORITHM,
        "left_model_family": LEFT_MODEL_FAMILY,
        "right_model_family": RIGHT_MODEL_FAMILY,
        "right_gate_feature": RIGHT_GATE_FEATURE,
        "soft_gate_feature": SOFT_GATE_FEATURE,
        "soft_gate_slope": SOFT_GATE_SLOPE,
        "soft_gate_offset_std": SOFT_GATE_OFFSET_STD,
        "soft_gate_boundary": round(boundary, 6),
        "drop_features": DROP_FEATURES,
        "extra_features": EXTRA_FEATURES,
        "threshold": round(SOFT_THRESHOLD, 4),
        "validation_f1": round(float(validation_metrics.f1), 4),
        "validation_bal_acc": round(float(validation_metrics.balanced_accuracy), 4),
        "test_f1": round(float(test_metrics.f1), 4),
        "test_bal_acc": round(float(test_metrics.balanced_accuracy), 4),
        "test_positive_rate": round(float(test_metrics.positive_rate), 4),
        "headline_score": round(
            float(
                rb.compute_headline_score(
                    validation_metrics.f1,
                    validation_metrics.balanced_accuracy,
                    test_metrics.f1,
                    test_metrics.balanced_accuracy,
                )
            ),
            4,
        ),
        "promotion_gate_passed": rb.passes_promotion_gate(
            float(validation_metrics.balanced_accuracy),
            float(test_metrics.balanced_accuracy),
        ),
    }


def main() -> None:
    payload = evaluate_winning_algorithm()
    output_path = Path(ac.get_cache_dir(ASSET_KEY)) / "nvda_topbottom12_5_soft_gate_two_expert.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))


if __name__ == "__main__":
    main()
