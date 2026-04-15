from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

import asset_config as ac
import prepare as pr
import research_batch as rb
import train as tr

ASSET_KEY = "slv"
BENCHMARK_SYMBOL = "GDX"
LABEL_MODE = "future-return-top-bottom-15pct"
LEFT_EXPERT = "gdx_relative_dual"
RIGHT_EXPERT = "gdx_context"
OUTER_GATE_FEATURE = "price_ratio_benchmark_z_20"
OUTER_GATE_THRESHOLD = 0.141332


def probabilities_to_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float32), 1e-6, 1.0 - 1.0e-6)
    return np.log(clipped / (1.0 - clipped))


def build_benchmark_relative_frame() -> tuple[pd.DataFrame, pd.DataFrame]:
    symbol = ac.get_asset_symbol(ASSET_KEY)
    raw = pr.download_symbol_prices(symbol, ac.stooq_url(symbol), str(ac.get_raw_data_path(ASSET_KEY)))
    frame = pr.add_price_features(raw)
    frame = pr.add_relative_strength_features(frame, BENCHMARK_SYMBOL)
    frame = pr.add_context_features(frame)
    frame = rb.add_regime_features(frame)
    labels, realized_returns = pr.build_barrier_labels(frame, 60, 0.12, -0.06)
    train_end, _ = pr.split_indices(len(frame))
    labels = pr.apply_label_mode(labels, realized_returns, LABEL_MODE, train_end=train_end)
    frame[pr.TARGET_COLUMN] = labels
    frame[rb.FUTURE_RETURN_COLUMN] = realized_returns
    selectable_experimental = [name for name in pr.EXPERIMENTAL_FEATURE_COLUMNS if name in frame.columns]
    needed = pr.FEATURE_COLUMNS + selectable_experimental + [rb.FUTURE_RETURN_COLUMN, pr.TARGET_COLUMN]
    frame = frame.replace([np.inf, -np.inf], np.nan)
    return raw, frame.dropna(subset=needed).reset_index(drop=True)


def evaluate_winning_algorithm() -> dict[str, float | str | bool | list[str]]:
    _, frame = build_benchmark_relative_frame()

    _, left_artifacts = rb.train_model(
        frame,
        LEFT_EXPERT,
        model_family="regime_dual_logistic",
        extra_features=(
            "ret_60",
            "sma_gap_60",
            "distance_to_252_high",
            "rs_vs_benchmark_60",
            "price_ratio_benchmark_z_20",
        ),
        gate_feature="above_200dma_flag",
    )
    _, right_artifacts = rb.train_model(
        frame,
        RIGHT_EXPERT,
        extra_features=(
            "ret_60",
            "sma_gap_60",
            "distance_to_252_high",
            "rs_vs_benchmark_60",
            "price_ratio_benchmark_z_20",
            "atr_pct_20_percentile",
        ),
    )

    splits = rb.split_frame(frame)
    validation = splits["validation"].reset_index(drop=True)
    test = splits["test"].reset_index(drop=True)
    validation_y = validation[pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    test_y = test[pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_returns = validation[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)
    test_returns = test[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)

    validation_mask = validation[OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= OUTER_GATE_THRESHOLD
    test_mask = test[OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= OUTER_GATE_THRESHOLD
    validation_probs = np.where(
        validation_mask,
        np.asarray(left_artifacts["validation_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["validation_probabilities"], dtype=np.float32),
    )
    test_probs = np.where(
        test_mask,
        np.asarray(left_artifacts["test_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["test_probabilities"], dtype=np.float32),
    )

    threshold = rb.select_threshold_with_steps(validation_probs, validation_y, tr.THRESHOLD_STEPS)
    validation_metrics = tr.compute_metrics(
        probabilities_to_logits(validation_probs),
        validation_y,
        validation_returns,
        threshold,
    )
    test_metrics = tr.compute_metrics(
        probabilities_to_logits(test_probs),
        test_y,
        test_returns,
        threshold,
    )

    return {
        "asset": ASSET_KEY,
        "benchmark_symbol": BENCHMARK_SYMBOL,
        "label_mode": LABEL_MODE,
        "algorithm": "hard_gate_two_expert",
        "left_expert": LEFT_EXPERT,
        "right_expert": RIGHT_EXPERT,
        "outer_gate_feature": OUTER_GATE_FEATURE,
        "outer_gate_threshold": round(OUTER_GATE_THRESHOLD, 6),
        "threshold": round(float(threshold), 4),
        "left_features": [
            "ret_60",
            "sma_gap_60",
            "distance_to_252_high",
            "rs_vs_benchmark_60",
            "price_ratio_benchmark_z_20",
        ],
        "right_features": [
            "ret_60",
            "sma_gap_60",
            "distance_to_252_high",
            "rs_vs_benchmark_60",
            "price_ratio_benchmark_z_20",
            "atr_pct_20_percentile",
        ],
        "validation_f1": round(float(validation_metrics.f1), 4),
        "validation_accuracy": round(float(validation_metrics.accuracy), 4),
        "validation_bal_acc": round(float(validation_metrics.balanced_accuracy), 4),
        "test_f1": round(float(test_metrics.f1), 4),
        "test_accuracy": round(float(test_metrics.accuracy), 4),
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
    output_path = Path(ac.get_cache_dir(ASSET_KEY)) / "slv_topbottom15_gdx_hard_gate_two_expert.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))


if __name__ == "__main__":
    main()
