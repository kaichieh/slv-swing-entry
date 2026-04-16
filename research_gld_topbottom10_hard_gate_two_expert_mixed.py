from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np

import asset_config as ac
import prepare as pr
import research_batch as rb
import train as tr

ASSET_KEY = "gld"
LABEL_MODE = "future-return-top-bottom-10pct"
LEFT_EXPERT = "dual_context"
RIGHT_EXPERT = "context_no_atr"
OUTER_GATE_FEATURE = "atr_pct_20_percentile"
OUTER_GATE_THRESHOLD = 0.70

LEFT_EXTRA_FEATURES = (
    "ret_60",
    "sma_gap_60",
    "trend_quality_20",
    "percent_up_days_20",
    "bollinger_bandwidth_20",
    "distance_from_60d_low",
    "atr_pct_20_percentile",
    "above_200dma_flag",
)

RIGHT_EXTRA_FEATURES = (
    "ret_60",
    "sma_gap_60",
    "trend_quality_20",
    "percent_up_days_20",
    "bollinger_bandwidth_20",
    "distance_from_60d_low",
)


def append_selected_experimental_features(default_features: tuple[str, ...], available_columns) -> tuple[str, ...]:
    selected = set(pr.get_env_csv("AR_EXTRA_BASE_FEATURES"))
    feature_names = list(default_features)
    for column in pr.EXPERIMENTAL_FEATURE_COLUMNS:
        if column not in selected or column not in available_columns or column in feature_names:
            continue
        feature_names.append(column)
    return tuple(feature_names)


def selected_vix_features_requested() -> bool:
    selected = set(pr.get_env_csv("AR_EXTRA_BASE_FEATURES"))
    return any(column.startswith("vix_") for column in selected)


def probabilities_to_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float32), 1e-6, 1.0 - 1.0e-6)
    return np.log(clipped / (1.0 - clipped))


def evaluate_winning_algorithm() -> dict[str, float | str]:
    symbol = ac.get_asset_symbol(ASSET_KEY)
    raw = pr.download_symbol_prices(symbol, ac.stooq_url(symbol), str(ac.get_raw_data_path(ASSET_KEY)))
    frame = rb.build_labeled_frame(raw, label_mode=LABEL_MODE)
    if selected_vix_features_requested():
        frame = pr.add_vix_features(frame, pr.download_vix_prices())
    left_extra_features = append_selected_experimental_features(LEFT_EXTRA_FEATURES, frame.columns)
    right_extra_features = append_selected_experimental_features(RIGHT_EXTRA_FEATURES, frame.columns)

    _, left_artifacts = rb.train_model(
        frame,
        LEFT_EXPERT,
        model_family="regime_dual_logistic",
        extra_features=left_extra_features,
        gate_feature="above_200dma_flag",
    )
    _, right_artifacts = rb.train_model(
        frame,
        RIGHT_EXPERT,
        extra_features=right_extra_features,
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
        "label_mode": LABEL_MODE,
        "algorithm": "hard_gate_two_expert_mixed",
        "left_expert": LEFT_EXPERT,
        "right_expert": RIGHT_EXPERT,
        "outer_gate_feature": OUTER_GATE_FEATURE,
        "outer_gate_threshold": round(OUTER_GATE_THRESHOLD, 4),
        "threshold": round(float(threshold), 4),
        "validation_f1": round(float(validation_metrics.f1), 4),
        "validation_bal_acc": round(float(validation_metrics.balanced_accuracy), 4),
        "validation_positive_rate": round(float(validation_metrics.positive_rate), 4),
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
    output_path = Path(ac.get_cache_dir(ASSET_KEY)) / "gld_topbottom10_hard_gate_two_expert_mixed.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))


if __name__ == "__main__":
    main()
