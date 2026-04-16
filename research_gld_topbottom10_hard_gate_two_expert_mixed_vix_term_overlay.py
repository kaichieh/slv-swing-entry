from __future__ import annotations

import json
from pathlib import Path
from typing import cast
import numpy as np
import pandas as pd

import asset_config as ac
import prepare as pr
import predict_latest as pl
import research_batch as rb
import research_gld_topbottom10_hard_gate_two_expert_mixed as base

ASSET_KEY = "gld"
TERM_FILTER_FEATURE = "vix_vxv_ratio_pct_63"
TERM_PANIC_BLOCK_MAX = float(cast(float | int | str, ac.get_live_term_panic_settings(ASSET_KEY)["threshold"] or 0.90))
TERM_PANIC_BLOCK_DAYS = 3


def build_research_frame() -> pd.DataFrame:
    symbol = ac.get_asset_symbol(ASSET_KEY)
    raw = pr.download_symbol_prices(symbol, ac.stooq_url(symbol), str(ac.get_raw_data_path(ASSET_KEY)))
    frame = rb.build_labeled_frame(raw, label_mode=base.LABEL_MODE)
    frame = pr.add_vix_features(frame, pr.download_vix_prices())
    frame = pr.add_vix_term_structure_features(frame, pr.download_vix3m_prices())
    return frame


def build_term_overlay_mask(frame: pd.DataFrame, base_selected: np.ndarray) -> np.ndarray:
    panic_window = pd.Series(frame[TERM_FILTER_FEATURE].to_numpy(dtype=np.float32)).rolling(TERM_PANIC_BLOCK_DAYS).max().fillna(0.0)
    return np.asarray(base_selected, dtype=bool) & ~(panic_window.to_numpy(dtype=np.float32) > TERM_PANIC_BLOCK_MAX)


def fit_baseline_probabilities(frame: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, np.ndarray, np.ndarray, float]:
    _, left_artifacts = rb.train_model(
        frame,
        base.LEFT_EXPERT,
        model_family="regime_dual_logistic",
        extra_features=base.LEFT_EXTRA_FEATURES,
        gate_feature="above_200dma_flag",
    )
    _, right_artifacts = rb.train_model(
        frame,
        base.RIGHT_EXPERT,
        extra_features=base.RIGHT_EXTRA_FEATURES,
    )
    splits = rb.split_frame(frame)
    validation = splits["validation"].reset_index(drop=True)
    test = splits["test"].reset_index(drop=True)
    validation_mask = validation[base.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= base.OUTER_GATE_THRESHOLD
    test_mask = test[base.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= base.OUTER_GATE_THRESHOLD
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
    threshold = float(
        rb.select_threshold_with_steps(
            validation_probs,
            validation[pr.TARGET_COLUMN].to_numpy(dtype=np.float32),
            rb.tr.THRESHOLD_STEPS,
        )
    )
    return validation, test, validation_probs, test_probs, threshold


def summarize_rule(test: pd.DataFrame, probabilities: np.ndarray, threshold: float, *, filtered: bool) -> dict[str, float | int | str]:
    selected, cutoff = rb.classify_probs_by_rule(probabilities, threshold, "top_20pct")
    mask = build_term_overlay_mask(test, np.asarray(selected, dtype=bool)) if filtered else np.asarray(selected, dtype=bool)
    backtest = rb.run_non_overlap_backtest(
        pd.Series(test["date"].to_numpy(copy=True)),
        test[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64),
        mask,
        pr.HORIZON_DAYS,
        float(cutoff),
    )
    return {
        "selected_count": int(backtest.selected_count),
        "hit_rate": round(float(backtest.hit_rate), 4),
        "avg_return": round(float(backtest.avg_return), 4),
        "max_drawdown_compound": round(float(backtest.max_drawdown_compound), 4),
        "filter": "term_overlay" if filtered else "none",
    }


def summarize_live_rule(test: pd.DataFrame, probabilities: np.ndarray, threshold: float, history_probabilities: np.ndarray, *, term_overlay: bool) -> dict[str, float | int | str]:
    selections: list[bool] = []
    for idx in range(len(test)):
        snapshot = {name: float(test.iloc[idx][name]) for name in test.columns if name != "date"}
        raw_signal, _band_info = pl.classify_signal(float(probabilities[idx]), float(threshold), history_probabilities)
        signal, _summary = pl.apply_buy_point_overlay(raw_signal, snapshot, asset_key="gld" if term_overlay else "")
        selections.append(signal != "no_entry")
    backtest = rb.run_non_overlap_backtest(
        pd.Series(test["date"].to_numpy(copy=True)),
        test[rb.FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64),
        np.asarray(selections, dtype=bool),
        pr.HORIZON_DAYS,
        float(threshold),
    )
    return {
        "selected_count": int(backtest.selected_count),
        "hit_rate": round(float(backtest.hit_rate), 4),
        "avg_return": round(float(backtest.avg_return), 4),
        "max_drawdown_compound": round(float(backtest.max_drawdown_compound), 4),
        "filter": "term_overlay" if term_overlay else "none",
    }


def evaluate_walkforward_overlay(frame: pd.DataFrame) -> dict[str, object]:
    n = len(frame)
    train_end = int(n * 0.55)
    step = max(60, (n - train_end - 120) // 5)
    start = train_end
    rows: list[dict[str, float | int | str]] = []
    while start + 120 <= n:
        sub = frame.iloc[: start + 120].reset_index(drop=True)
        validation, test, validation_probs, test_probs, threshold = fit_baseline_probabilities(sub)
        baseline_rule = summarize_rule(test, test_probs, threshold, filtered=False)
        filtered_rule = summarize_rule(test, test_probs, threshold, filtered=True)
        rows.append({"filter": "none", **baseline_rule})
        rows.append({"filter": "term_overlay", **filtered_rule})
        start += step

    def summarize(name: str) -> dict[str, object]:
        subset = [row for row in rows if row["filter"] == name]
        return {
            "filter": name,
            "folds": len(subset),
            "total_selected": int(sum(int(row["selected_count"]) for row in subset)),
            "mean_avg_return": round(float(np.mean([float(row["avg_return"]) for row in subset])), 4),
            "mean_hit_rate": round(float(np.mean([float(row["hit_rate"]) for row in subset])), 4),
        }

    return {"baseline": summarize("none"), "term_overlay": summarize("term_overlay")}


def evaluate_term_overlay() -> dict[str, object]:
    frame = build_research_frame()
    validation, test, validation_probs, test_probs, threshold = fit_baseline_probabilities(frame)
    baseline_rule = summarize_rule(test, test_probs, threshold, filtered=False)
    filtered_rule = summarize_rule(test, test_probs, threshold, filtered=True)
    history_probabilities = np.concatenate([validation_probs, test_probs]).astype(np.float32)
    baseline_live_rule = summarize_live_rule(test, test_probs, threshold, history_probabilities, term_overlay=False)
    term_live_rule = summarize_live_rule(test, test_probs, threshold, history_probabilities, term_overlay=True)
    walkforward = evaluate_walkforward_overlay(frame)
    return {
        "asset": ASSET_KEY,
        "label_mode": base.LABEL_MODE,
        "algorithm": "hard_gate_two_expert_mixed_vix_term_overlay",
        "term_filter_feature": TERM_FILTER_FEATURE,
        "term_panic_block_max": TERM_PANIC_BLOCK_MAX,
        "term_panic_block_days": TERM_PANIC_BLOCK_DAYS,
        "threshold": round(float(threshold), 4),
        "baseline_rule": baseline_rule,
        "term_filtered_rule": filtered_rule,
        "baseline_live_rule": baseline_live_rule,
        "term_live_rule": term_live_rule,
        "walkforward": walkforward,
    }


def main() -> None:
    payload = evaluate_term_overlay()
    output_path = Path(ac.get_cache_dir(ASSET_KEY)) / "gld_topbottom10_hard_gate_two_expert_mixed_vix_term_overlay.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"output_path": str(output_path), **payload}, indent=2))


if __name__ == "__main__":
    main()
