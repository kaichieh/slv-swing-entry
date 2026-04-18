"""
Score the latest available asset daily bar without requiring future labels.

Default live config starts from the baseline feature set only.
"""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Mapping, cast

import numpy as np

import asset_config as ac
import train as tr
from prepare import (
    BENCHMARK_SYMBOL,
    DatasetSplit,
    add_context_features,
    add_price_features,
    add_relative_strength_features,
    add_vix_term_structure_features,
    add_vix_features,
    download_asset_prices,
    download_vix3m_prices,
    download_vix_prices,
)

DEFAULT_LIVE_EXTRA_FEATURES = ac.get_live_extra_features()
WEAK_BULLISH_QUANTILE = 0.70
BULLISH_QUANTILE = 0.90
VERY_STRONG_BULLISH_QUANTILE = 0.97
RULE_TOP_PCT = 20.0
HARD_GATE_TWO_EXPERT = "hard_gate_two_expert"
HARD_GATE_TWO_EXPERT_MIXED = "hard_gate_two_expert_mixed"
HARD_GATE_TWO_EXPERT_GDX_LIVE = "hard_gate_two_expert_gdx_live"
GLD_CURRENT_LIVE_MIXED_LIVE = "gld_current_live_mixed_live"
GLD_MIXED_VIX_TERM_PANIC_LIVE = "gld_mixed_vix_vxv_term_panic_live"
LIVE_OPERATOR_FEATURE_MAP = {
    "ret_60_sma_gap_60_atr_pct_20": {"ret_60", "sma_gap_60", "atr_pct_20"},
    "xgboost_tb30_distance_live": {"distance_to_252_high"},
    "mu_tb30_ret_60_vol_ratio_20_120_top12_5": {"ret_60", "vol_ratio_20_120"},
}
LIVE_OPERATOR_MODEL_FAMILY_MAP = {
    HARD_GATE_TWO_EXPERT_GDX_LIVE: HARD_GATE_TWO_EXPERT,
    GLD_MIXED_VIX_TERM_PANIC_LIVE: HARD_GATE_TWO_EXPERT_MIXED,
    GLD_CURRENT_LIVE_MIXED_LIVE: HARD_GATE_TWO_EXPERT_MIXED,
}

try:
    _XGBOOST_MODULE = importlib.import_module("xgboost")
    _XGBOOST_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised through runtime path/tests
    _XGBOOST_MODULE = None
    _XGBOOST_IMPORT_ERROR = exc


def build_feature_names() -> list[str]:
    feature_names = list(tr.FEATURE_COLUMNS)
    configured = set(tr.get_env_csv("AR_EXTRA_BASE_FEATURES", DEFAULT_LIVE_EXTRA_FEATURES))
    for column in tr.EXPERIMENTAL_FEATURE_COLUMNS:
        if column in configured:
            feature_names.append(column)
    drop_features = set(tr.get_env_csv("AR_DROP_FEATURES"))
    return [name for name in feature_names if name not in drop_features]


def append_selected_experimental_features(default_features: tuple[str, ...], available_columns) -> tuple[str, ...]:
    selected = set(tr.get_env_csv("AR_EXTRA_BASE_FEATURES"))
    feature_names = list(default_features)
    for column in tr.EXPERIMENTAL_FEATURE_COLUMNS:
        if column not in selected or column not in available_columns or column in feature_names:
            continue
        feature_names.append(column)
    return tuple(feature_names)


def selected_vix_features_requested() -> bool:
    selected = set(tr.get_env_csv("AR_EXTRA_BASE_FEATURES"))
    return any(column.startswith("vix_") for column in selected)


def get_rule_top_pct() -> float:
    configured = ac.load_asset_config().get("live_reference_top_pct")
    if configured is None:
        return RULE_TOP_PCT
    try:
        value = float(cast(float | int | str, configured))
    except (TypeError, ValueError):
        return RULE_TOP_PCT
    return value if 0.0 < value < 100.0 else RULE_TOP_PCT


def get_live_label_mode() -> str:
    config = ac.load_asset_config()
    value = str(config.get("live_label_mode", config.get("label_mode", "drop-neutral"))).strip()
    return value if value else str(config.get("label_mode", "drop-neutral"))


def get_live_operator_line_id() -> str:
    value = str(ac.load_asset_config().get("live_operator_line_id", "")).strip()
    return value


def get_live_benchmark_symbol() -> str:
    configured = str(ac.load_asset_config().get("benchmark_symbol", "")).strip().upper()
    if configured:
        return configured
    return BENCHMARK_SYMBOL


def resolve_live_operator_line_id(feature_names: list[str], model_family: str) -> str:
    configured_line = get_live_operator_line_id()
    if not configured_line:
        return ""
    expected_family = LIVE_OPERATOR_MODEL_FAMILY_MAP.get(configured_line)
    if expected_family is not None:
        return configured_line if model_family == expected_family else ""
    expected_features = LIVE_OPERATOR_FEATURE_MAP.get(configured_line)
    if expected_features is None:
        return ""
    actual_features = {name for name in feature_names if name not in tr.FEATURE_COLUMNS}
    return configured_line if actual_features == expected_features else ""


def get_gld_mixed_live_source_module_name() -> str:
    return (
        "research_gld_current_live_mixed_baseline"
        if get_live_operator_line_id() in {"", GLD_CURRENT_LIVE_MIXED_LIVE}
        else "research_gld_topbottom10_hard_gate_two_expert_mixed"
    )


def uses_gld_term_panic_overlay(live_operator_line_id: str, model_family: str) -> bool:
    return model_family == HARD_GATE_TWO_EXPERT_MIXED and live_operator_line_id == GLD_MIXED_VIX_TERM_PANIC_LIVE


def active_gld_term_panic_overlay(asset_key: str) -> bool:
    return asset_key == "gld" and uses_gld_term_panic_overlay(
        ac.get_live_operator_line_id(asset_key),
        ac.get_live_model_family(asset_key),
    )


def build_live_provenance(model_artifacts: Mapping[str, Any], live_operator_line_id: str) -> dict[str, object]:
    model_family = str(model_artifacts.get("model_family", "")).strip()
    if model_family not in {HARD_GATE_TWO_EXPERT, HARD_GATE_TWO_EXPERT_MIXED}:
        return {}
    provenance = {
        "operator_line_id": live_operator_line_id,
        "benchmark_symbol": get_live_benchmark_symbol(),
        "outer_gate_feature": str(model_artifacts.get("outer_gate_feature", "")),
        "outer_gate_threshold": round(float(cast(float | int | str, model_artifacts.get("outer_gate_threshold", 0.0))), 6),
        "left_expert": str(model_artifacts.get("left_expert", "")),
        "right_expert": str(model_artifacts.get("right_expert", "")),
    }
    if uses_gld_term_panic_overlay(live_operator_line_id, model_family):
        settings = ac.get_live_term_panic_settings()
        if settings["feature"] and settings["threshold"] is not None:
            provenance["decision_overlay"] = "vix_vxv_term_panic_block"
            provenance["term_panic_feature"] = str(settings["feature"])
            provenance["term_panic_threshold"] = round(float(cast(float | int | str, settings["threshold"])), 6)
    return provenance


def require_xgboost() -> Any:
    if _XGBOOST_MODULE is not None:
        return _XGBOOST_MODULE
    detail = f": {_XGBOOST_IMPORT_ERROR}" if _XGBOOST_IMPORT_ERROR is not None else ""
    raise ModuleNotFoundError(f"xgboost is required for the XGBoost live path{detail}")


def get_live_model_family() -> str:
    family = ac.get_live_model_family()
    if family not in {"logistic", "xgboost", HARD_GATE_TWO_EXPERT, HARD_GATE_TWO_EXPERT_MIXED}:
        raise ValueError(f"Unsupported live_model_family '{family}'")
    return family


def get_live_execution_rule() -> str:
    return ac.get_live_execution_rule()


def get_live_threshold_metric() -> str:
    return ac.get_live_threshold_metric()


def fit_hard_gate_two_expert_model(raw_prices) -> dict[str, Any]:
    import research_batch as rb
    import research_slv_topbottom15_gdx_hard_gate_two_expert as winner

    left_extra_features = (
        "ret_60",
        "sma_gap_60",
        "distance_to_252_high",
        "rs_vs_benchmark_60",
        "price_ratio_benchmark_z_20",
    )
    right_extra_features = (
        "ret_60",
        "sma_gap_60",
        "distance_to_252_high",
        "rs_vs_benchmark_60",
        "price_ratio_benchmark_z_20",
        "atr_pct_20_percentile",
    )

    frame = rb.build_labeled_frame(raw_prices, label_mode=get_live_label_mode())
    left_extra_features = append_selected_experimental_features(left_extra_features, frame.columns)
    right_extra_features = append_selected_experimental_features(right_extra_features, frame.columns)
    _, left_artifacts = rb.train_model(
        frame,
        winner.LEFT_EXPERT,
        model_family="regime_dual_logistic",
        extra_features=left_extra_features,
        gate_feature="above_200dma_flag",
    )
    _, right_artifacts = rb.train_model(
        frame,
        winner.RIGHT_EXPERT,
        extra_features=right_extra_features,
    )

    splits = rb.split_frame(frame)
    validation = splits["validation"].reset_index(drop=True)
    test = splits["test"].reset_index(drop=True)
    validation_y = validation[tr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_mask = validation[winner.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= winner.OUTER_GATE_THRESHOLD
    test_mask = test[winner.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= winner.OUTER_GATE_THRESHOLD
    validation_probabilities = np.where(
        validation_mask,
        np.asarray(left_artifacts["validation_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["validation_probabilities"], dtype=np.float32),
    )
    test_probabilities = np.where(
        test_mask,
        np.asarray(left_artifacts["test_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["test_probabilities"], dtype=np.float32),
    )
    feature_names = list(dict.fromkeys([*left_artifacts["feature_names"], *right_artifacts["feature_names"]]))
    threshold = float(rb.select_threshold_with_steps(validation_probabilities, validation_y, tr.THRESHOLD_STEPS))

    return {
        "model_family": HARD_GATE_TWO_EXPERT,
        "threshold": threshold,
        "train_frame": splits["train"],
        "feature_names": feature_names,
        "left_artifacts": left_artifacts,
        "right_artifacts": right_artifacts,
        "left_expert": winner.LEFT_EXPERT,
        "right_expert": winner.RIGHT_EXPERT,
        "outer_gate_feature": winner.OUTER_GATE_FEATURE,
        "outer_gate_threshold": float(winner.OUTER_GATE_THRESHOLD),
        "validation_probabilities": validation_probabilities,
        "test_probabilities": test_probabilities,
        "live_label_mode": get_live_label_mode(),
        "default_interactions": [],
        "trained_until_label_date": test["date"].iloc[-1].strftime("%Y-%m-%d"),
    }


def fit_hard_gate_two_expert_mixed_model(raw_prices) -> dict[str, Any]:
    import research_batch as rb

    winner = importlib.import_module(get_gld_mixed_live_source_module_name())

    frame = rb.build_labeled_frame(raw_prices, label_mode=get_live_label_mode())
    if selected_vix_features_requested():
        frame = add_vix_features(frame, download_vix_prices())
    left_extra_features = append_selected_experimental_features(winner.LEFT_EXTRA_FEATURES, frame.columns)
    right_extra_features = append_selected_experimental_features(winner.RIGHT_EXTRA_FEATURES, frame.columns)
    _, left_artifacts = rb.train_model(
        frame,
        winner.LEFT_EXPERT,
        model_family="regime_dual_logistic",
        extra_features=left_extra_features,
        gate_feature="above_200dma_flag",
    )
    _, right_artifacts = rb.train_model(
        frame,
        winner.RIGHT_EXPERT,
        extra_features=right_extra_features,
    )

    splits = rb.split_frame(frame)
    validation = splits["validation"].reset_index(drop=True)
    test = splits["test"].reset_index(drop=True)
    validation_y = validation[tr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_mask = validation[winner.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= winner.OUTER_GATE_THRESHOLD
    test_mask = test[winner.OUTER_GATE_FEATURE].to_numpy(dtype=np.float32) >= winner.OUTER_GATE_THRESHOLD
    validation_probabilities = np.where(
        validation_mask,
        np.asarray(left_artifacts["validation_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["validation_probabilities"], dtype=np.float32),
    )
    test_probabilities = np.where(
        test_mask,
        np.asarray(left_artifacts["test_probabilities"], dtype=np.float32),
        np.asarray(right_artifacts["test_probabilities"], dtype=np.float32),
    )
    feature_names = list(dict.fromkeys([*left_artifacts["feature_names"], *right_artifacts["feature_names"]]))
    threshold = float(rb.select_threshold_with_steps(validation_probabilities, validation_y, tr.THRESHOLD_STEPS))

    return {
        "model_family": HARD_GATE_TWO_EXPERT_MIXED,
        "threshold": threshold,
        "train_frame": splits["train"],
        "feature_names": feature_names,
        "left_artifacts": left_artifacts,
        "right_artifacts": right_artifacts,
        "left_expert": winner.LEFT_EXPERT,
        "right_expert": winner.RIGHT_EXPERT,
        "outer_gate_feature": winner.OUTER_GATE_FEATURE,
        "outer_gate_threshold": float(winner.OUTER_GATE_THRESHOLD),
        "validation_probabilities": validation_probabilities,
        "test_probabilities": test_probabilities,
        "live_label_mode": get_live_label_mode(),
        "default_interactions": [],
        "trained_until_label_date": test["date"].iloc[-1].strftime("%Y-%m-%d"),
    }


def fit_logistic_model(splits: Mapping[str, DatasetSplit], feature_names: list[str]) -> dict[str, Any]:
    train_x = splits["train"].frame[feature_names].to_numpy(dtype=np.float32)
    validation_x = splits["validation"].frame[feature_names].to_numpy(dtype=np.float32)
    train_y = splits["train"].labels
    validation_y = splits["validation"].labels

    train_x, validation_x, _ = tr.standardize(train_x, validation_x, validation_x.copy())
    train_x, validation_x, _ = tr.add_interaction_terms(train_x, validation_x, validation_x.copy(), feature_names)
    train_x = tr.add_bias(train_x)
    validation_x = tr.add_bias(validation_x)

    learning_rate = tr.get_env_float("AR_LEARNING_RATE", tr.LEARNING_RATE)
    l2_reg = tr.get_env_float("AR_L2_REG", tr.L2_REG)
    pos_weight = tr.get_env_float("AR_POS_WEIGHT", tr.POS_WEIGHT)
    neg_weight = tr.get_env_float("AR_NEG_WEIGHT", tr.NEG_WEIGHT)
    max_epochs = tr.get_env_int("AR_MAX_EPOCHS", tr.MAX_EPOCHS)
    patience_limit = tr.get_env_int("AR_PATIENCE", tr.PATIENCE)

    weights = np.zeros(train_x.shape[1], dtype=np.float32)
    best_weights = weights.copy()
    best_validation_f1 = -np.inf
    best_threshold = 0.5
    epochs_without_improvement = 0
    threshold_metric = get_live_threshold_metric()

    validation_returns = splits["validation"].frame["future_return_60"].to_numpy(dtype=np.float32)

    for _epoch in range(1, max_epochs + 1):
        logits = train_x @ weights
        probs = tr.sigmoid(logits)
        sample_weights = np.where(train_y == 1.0, pos_weight, neg_weight).astype(np.float32)
        gradient = train_x.T @ ((probs - train_y) * sample_weights) / train_x.shape[0]
        gradient[:-1] += l2_reg * weights[:-1]
        weights -= learning_rate * gradient

        validation_logits = validation_x @ weights
        threshold = tr.select_threshold(tr.sigmoid(validation_logits), validation_y, primary_metric=threshold_metric)
        validation_metrics = tr.compute_metrics(validation_logits, validation_y, validation_returns, threshold)
        if validation_metrics.f1 > best_validation_f1:
            best_validation_f1 = validation_metrics.f1
            best_weights = weights.copy()
            best_threshold = threshold
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= patience_limit:
            break

    return {
        "model_family": "logistic",
        "model": best_weights,
        "threshold": float(best_threshold),
        "train_frame": splits["train"].frame,
        "feature_names": feature_names,
        "default_interactions": ["drawdown_20:volume_vs_20"],
        "threshold_metric": threshold_metric,
    }


def fit_xgboost_model(splits: Mapping[str, DatasetSplit], feature_names: list[str]) -> dict[str, Any]:
    xgb = require_xgboost()
    train_x = splits["train"].frame[feature_names].to_numpy(dtype=np.float32)
    validation_x = splits["validation"].frame[feature_names].to_numpy(dtype=np.float32)
    train_y = splits["train"].labels.astype(np.float32)
    validation_y = splits["validation"].labels.astype(np.float32)
    params = ac.get_live_xgboost_params()
    n_estimators = int(params.get("n_estimators", 200))
    max_depth = int(params.get("max_depth", 3))
    learning_rate = float(params.get("learning_rate", 0.05))

    if hasattr(xgb, "DMatrix") and hasattr(xgb, "train"):
        train_matrix = xgb.DMatrix(train_x, label=train_y)
        validation_matrix = xgb.DMatrix(validation_x, label=validation_y)
        model = xgb.train(
            {
                "objective": "binary:logistic",
                "eval_metric": "logloss",
                "max_depth": max_depth,
                "eta": learning_rate,
                "subsample": 1.0,
                "colsample_bytree": 1.0,
                "lambda": 1.0,
                "seed": tr.SEED,
            },
            train_matrix,
            num_boost_round=n_estimators,
        )
        validation_probabilities = np.asarray(model.predict(validation_matrix), dtype=np.float32)
    else:
        model = xgb.XGBClassifier(
            objective="binary:logistic",
            eval_metric="logloss",
            n_estimators=n_estimators,
            max_depth=max_depth,
            learning_rate=learning_rate,
            subsample=1.0,
            colsample_bytree=1.0,
            reg_lambda=1.0,
            random_state=tr.SEED,
        )
        model.fit(train_x, train_y)
        validation_probabilities = np.asarray(model.predict_proba(validation_x)[:, 1], dtype=np.float32)

    threshold_metric = get_live_threshold_metric()
    threshold = tr.select_threshold(validation_probabilities, validation_y, primary_metric=threshold_metric)
    return {
        "model_family": "xgboost",
        "model": model,
        "threshold": float(threshold),
        "train_frame": splits["train"].frame,
        "feature_names": feature_names,
        "xgboost_params": {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
        },
        "default_interactions": [],
        "threshold_metric": threshold_metric,
    }


def fit_model(splits: Mapping[str, DatasetSplit], feature_names: list[str], raw_prices=None) -> dict[str, Any]:
    family = get_live_model_family()
    if family == HARD_GATE_TWO_EXPERT:
        if raw_prices is None:
            raise ValueError("raw_prices is required for hard_gate_two_expert live path")
        return fit_hard_gate_two_expert_model(raw_prices)
    if family == HARD_GATE_TWO_EXPERT_MIXED:
        if raw_prices is None:
            raise ValueError("raw_prices is required for hard_gate_two_expert_mixed live path")
        return fit_hard_gate_two_expert_mixed_model(raw_prices)
    if family == "xgboost":
        return fit_xgboost_model(splits, feature_names)
    return fit_logistic_model(splits, feature_names)


def score_research_model_probabilities(artifacts: Mapping[str, Any], frame) -> np.ndarray:
    import research_batch as rb

    if len(frame) == 0:
        return np.asarray([], dtype=np.float32)
    feature_names = list(cast(list[str], artifacts["feature_names"]))
    matrix = frame[feature_names].to_numpy(dtype=np.float32)
    mean = np.asarray(artifacts["train_mean"], dtype=np.float32)
    std = np.asarray(artifacts["train_std"], dtype=np.float32)
    standardized = (matrix - mean) / std
    pair_indices = cast(tuple[tuple[int, int], ...], artifacts.get("pair_indices", ()))
    standardized = rb.add_interactions(standardized, pair_indices)
    standardized = tr.add_bias(standardized)
    model_family = str(artifacts["model_family"])
    if model_family == "regime_dual_logistic":
        gate_feature = str(artifacts["gate_feature"])
        positive_mask = frame[gate_feature].to_numpy(dtype=np.float32) >= 0.5
        logits = np.empty(len(frame), dtype=np.float32)
        negative_weights = np.asarray(artifacts["negative_weights"], dtype=np.float32)
        positive_weights = np.asarray(artifacts["positive_weights"], dtype=np.float32)
        logits[positive_mask] = standardized[positive_mask] @ positive_weights
        logits[~positive_mask] = standardized[~positive_mask] @ negative_weights
        return tr.sigmoid(logits)
    weights = np.asarray(artifacts["weights"], dtype=np.float32)
    return tr.sigmoid(standardized @ weights)


def score_hard_gate_two_expert_mixed_probabilities(model_artifacts: Mapping[str, Any], frame) -> np.ndarray:
    left_probabilities = score_research_model_probabilities(cast(Mapping[str, Any], model_artifacts["left_artifacts"]), frame)
    right_probabilities = score_research_model_probabilities(cast(Mapping[str, Any], model_artifacts["right_artifacts"]), frame)
    outer_gate_feature = str(model_artifacts["outer_gate_feature"])
    outer_gate_threshold = float(model_artifacts["outer_gate_threshold"])
    outer_mask = frame[outer_gate_feature].to_numpy(dtype=np.float32) >= outer_gate_threshold
    return np.where(outer_mask, left_probabilities, right_probabilities)


def score_latest_row(model_artifacts: dict[str, Any], feature_names: list[str], train_frame, latest_row) -> tuple[np.ndarray, dict[str, float]]:
    model_family = str(model_artifacts["model_family"])
    if model_family in {HARD_GATE_TWO_EXPERT, HARD_GATE_TWO_EXPERT_MIXED}:
        raw_snapshot = {name: float(latest_row.iloc[0][name]) for name in latest_row.columns if name != "date"}
        return latest_row.copy(), raw_snapshot
    train_x = train_frame[feature_names].to_numpy(dtype=np.float32)
    latest_x = latest_row[feature_names].to_numpy(dtype=np.float32)
    raw_snapshot = {name: float(latest_row.iloc[0][name]) for name in latest_row.columns if name != "date"}
    if model_family == "xgboost":
        return latest_x, raw_snapshot
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    standardized_latest = (latest_x - mean) / std
    _, _, latest_augmented = tr.add_interaction_terms(train_x[:1], train_x[:1], standardized_latest, feature_names)
    latest_augmented = tr.add_bias(latest_augmented)
    return latest_augmented, raw_snapshot


def predict_probabilities(model_artifacts: dict[str, Any], matrix) -> np.ndarray:
    model_family = str(model_artifacts["model_family"])
    if model_family in {HARD_GATE_TWO_EXPERT, HARD_GATE_TWO_EXPERT_MIXED}:
        return score_hard_gate_two_expert_mixed_probabilities(model_artifacts, matrix)
    model = model_artifacts["model"]
    if model_family == "xgboost":
        xgb = require_xgboost()
        dmatrix = getattr(xgb, "DMatrix", None)
        if callable(dmatrix) and hasattr(model, "predict"):
            return np.asarray(model.predict(dmatrix(matrix)), dtype=np.float32)
        return np.asarray(model.predict_proba(matrix)[:, 1], dtype=np.float32)
    return tr.sigmoid(matrix @ model)


def build_history_probabilities(
    model_artifacts: dict[str, Any], splits: Mapping[str, DatasetSplit], feature_names: list[str]
) -> np.ndarray:
    if str(model_artifacts["model_family"]) in {HARD_GATE_TWO_EXPERT, HARD_GATE_TWO_EXPERT_MIXED}:
        return np.concatenate(
            [
                np.asarray(model_artifacts["validation_probabilities"], dtype=np.float32),
                np.asarray(model_artifacts["test_probabilities"], dtype=np.float32),
            ]
        )
    history_probs: list[np.ndarray] = []
    train_frame = model_artifacts["train_frame"]
    for split_name in ("validation", "test"):
        split_frame = splits[split_name].frame
        matrix, _ = score_latest_row(model_artifacts, feature_names, train_frame, split_frame)
        history_probs.append(predict_probabilities(model_artifacts, matrix))
    return np.concatenate(history_probs)


def classify_signal(probability: float, threshold: float, historical_probabilities: np.ndarray) -> tuple[str, dict[str, float]]:
    confidence_gap = probability - threshold
    historical_gaps = historical_probabilities - threshold
    positive_gaps = historical_gaps[historical_gaps > 0]
    weak_cutoff = float(np.quantile(positive_gaps, WEAK_BULLISH_QUANTILE)) if len(positive_gaps) else 0.0
    strong_cutoff = float(np.quantile(positive_gaps, BULLISH_QUANTILE)) if len(positive_gaps) else 0.0
    very_strong_cutoff = float(np.quantile(positive_gaps, VERY_STRONG_BULLISH_QUANTILE)) if len(positive_gaps) else 0.0

    if confidence_gap <= 0:
        signal = "no_entry"
    elif confidence_gap >= very_strong_cutoff:
        signal = "very_strong_bullish"
    elif confidence_gap >= strong_cutoff:
        signal = "strong_bullish"
    elif confidence_gap >= weak_cutoff:
        signal = "bullish"
    else:
        signal = "weak_bullish"

    return signal, {
        "confidence_gap": round(confidence_gap, 4),
        "weak_bullish_cutoff": round(weak_cutoff, 4),
        "strong_bullish_cutoff": round(strong_cutoff, 4),
        "very_strong_bullish_cutoff": round(very_strong_cutoff, 4),
    }


def assess_buy_point(snapshot: dict[str, float]) -> tuple[bool, list[str], list[str]]:
    passes: list[str] = []
    warnings: list[str] = []

    rsi_14 = float(snapshot.get("rsi_14", 50.0))
    drawdown_20 = float(snapshot.get("drawdown_20", 0.0))
    ret_20 = float(snapshot.get("ret_20", 0.0))
    sma_gap_20 = float(snapshot.get("sma_gap_20", 0.0))

    if drawdown_20 <= -0.08:
        passes.append("近 20 日回檔夠深，開始接近可觀察的買點區")
    elif drawdown_20 >= -0.03:
        warnings.append("近 20 日回檔仍偏淺，較像追價不是撿回檔")

    if rsi_14 <= 45:
        passes.append("14 日 RSI 已降溫，沒有過熱追價感")
    elif rsi_14 >= 60:
        warnings.append("14 日 RSI 仍偏高，短線有點過熱")

    if ret_20 <= 0.02:
        passes.append("近 20 日動能沒有過度拉伸")
    elif ret_20 >= 0.08:
        warnings.append("近 20 日漲幅已偏大，容易落在追價區")

    if sma_gap_20 <= 0.01:
        passes.append("價格沒有明顯乖離 20 日均線")
    elif sma_gap_20 >= 0.05:
        warnings.append("價格明顯高於 20 日均線，乖離偏大")

    return len(warnings) == 0, passes, warnings


def apply_buy_point_overlay(signal: str, snapshot: dict[str, float], asset_key: str = "") -> tuple[str, dict[str, object]]:
    buy_point_ok, passes, warnings = assess_buy_point(snapshot)
    adjusted_signal = signal

    settings = ac.get_live_term_panic_settings(asset_key)
    term_panic_feature = str(settings["feature"]) if settings["feature"] else ""
    term_panic_threshold = settings["threshold"]
    term_panic = (
        active_gld_term_panic_overlay(asset_key)
        and bool(term_panic_feature)
        and term_panic_threshold is not None
        and float(snapshot.get(term_panic_feature, 0.0)) > float(cast(float | int | str, term_panic_threshold))
    )
    if term_panic:
        adjusted_signal = "no_entry"
        warnings = ["GLD term panic block active: recent VIX/VIX3M stress remains extreme"] + warnings
        buy_point_ok = False

    if not buy_point_ok and not term_panic:
        if signal in {"very_strong_bullish", "strong_bullish"}:
            adjusted_signal = "bullish"
        elif signal == "bullish":
            adjusted_signal = "weak_bullish"
        elif signal == "weak_bullish":
            adjusted_signal = "no_entry"

    return adjusted_signal, {
        "buy_point_ok": buy_point_ok,
        "buy_point_passes": passes,
        "buy_point_warnings": warnings,
    }


def summarize_rule(probability: float, historical_probabilities: np.ndarray, top_pct: float = RULE_TOP_PCT) -> dict[str, object]:
    cutoff = float(np.quantile(historical_probabilities, 1.0 - top_pct / 100.0)) if len(historical_probabilities) else 0.0
    percentile_rank = float((historical_probabilities <= probability).mean()) if len(historical_probabilities) else 0.0
    selected = probability >= cutoff
    return {
        "rule_name": f"top_{top_pct:g}pct_reference",
        "selected": bool(selected),
        "cutoff": round(cutoff, 4),
        "percentile_rank": round(percentile_rank, 4),
        "verdict": (
            f"Current score sits inside the historical top {top_pct:g}% of model probabilities"
            if selected
            else f"Current score does not reach the historical top {top_pct:g}% cutoff"
        ),
    }


def parse_top_pct_rule(rule_name: str) -> float | None:
    prefix = "top_"
    suffix = "pct"
    if not (rule_name.startswith(prefix) and rule_name.endswith(suffix)):
        return None
    raw = rule_name[len(prefix) : -len(suffix)].replace("_", ".")
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if 0.0 < value < 100.0 else None


def resolve_execution_cutoff(execution_rule: str, threshold: float, historical_probabilities: np.ndarray) -> float:
    if execution_rule == "threshold":
        return threshold
    top_pct = parse_top_pct_rule(execution_rule)
    if top_pct is not None:
        if len(historical_probabilities) == 0:
            return threshold
        return float(np.quantile(historical_probabilities, 1.0 - top_pct / 100.0))
    if execution_rule.startswith("fixed_"):
        try:
            return float(execution_rule.split("_", 1)[1])
        except ValueError:
            return threshold
    return threshold


def build_model_rationale(snapshot: dict[str, float]) -> list[str]:
    reasons: list[str] = []
    rsi_14 = float(snapshot.get("rsi_14", 50.0))
    drawdown_20 = float(snapshot.get("drawdown_20", 0.0))
    volume_vs_20 = float(snapshot.get("volume_vs_20", 0.0))
    sma_gap_60 = float(snapshot.get("sma_gap_60", 0.0))
    ret_60 = float(snapshot.get("ret_60", 0.0))

    if rsi_14 < 20:
        reasons.append("14 日 RSI 很低，已經有明顯超賣味道")
    elif rsi_14 < 30:
        reasons.append("14 日 RSI 偏弱，開始接近超賣區")
    elif rsi_14 > 70:
        reasons.append("14 日 RSI 偏高，短線有過熱跡象")

    if drawdown_20 <= -0.15:
        reasons.append("近 20 日跌幅很深，屬於急跌後區間")
    elif drawdown_20 <= -0.10:
        reasons.append("近 20 日已有一段像樣回檔")
    elif drawdown_20 >= -0.03:
        reasons.append("近 20 日幾乎沒什麼回檔，位置偏高")

    if volume_vs_20 >= 1.0:
        reasons.append("量能明顯高於 20 日均量，資金參與偏強")
    elif volume_vs_20 >= 0.2:
        reasons.append("量能略高於 20 日均量")

    if sma_gap_60 <= -0.08:
        reasons.append("價格明顯低於 60 日均線，屬於跌深區")
    elif sma_gap_60 <= -0.04:
        reasons.append("價格落在 60 日均線下方")
    elif sma_gap_60 >= 0.08:
        reasons.append("價格遠高於 60 日均線，較像高位延續")

    if ret_60 >= 0.03:
        reasons.append("近 60 日報酬仍為正，趨勢面還沒轉弱")
    elif ret_60 <= -0.03:
        reasons.append("近 60 日報酬偏弱，較像跌深後反彈型態")

    if not reasons:
        reasons.append("目前特徵偏中性，沒有特別明確的超賣或強勢優勢")
    return reasons


def build_rule_rationale(probability: float, threshold: float, rule_summary: dict[str, object]) -> str:
    rule_name = str(rule_summary.get("rule_name", "top_20pct_reference"))
    top_pct_text = "20"
    prefix = "top_"
    suffix = "pct_reference"
    if rule_name.startswith(prefix) and rule_name.endswith(suffix):
        top_pct_text = rule_name[len(prefix) : -len(suffix)].replace("_", ".")
    if probability < threshold:
        return "模型分數低於 threshold，規則上偏向先不進場"
    if bool(rule_summary["selected"]):
        return f"模型分數不只高於 threshold，也進入歷史前 {top_pct_text}% 強訊號區"
    return f"模型分數已高於 threshold，但還沒進入歷史前 {top_pct_text}% 強訊號區"


def main() -> None:
    tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
    asset_key = str(ac.load_asset_config()["asset_key"])
    raw_prices = download_asset_prices()
    live_features = add_context_features(add_relative_strength_features(add_price_features(raw_prices), BENCHMARK_SYMBOL))
    splits = tr.load_splits()
    feature_names = build_feature_names()
    if any(name.startswith("vix_") for name in feature_names):
        live_features = add_vix_features(live_features, download_vix_prices())
    if active_gld_term_panic_overlay(asset_key):
        live_features = add_vix_features(live_features, download_vix_prices())
        live_features = add_vix_term_structure_features(live_features, download_vix3m_prices())
    model_artifacts = fit_model(splits, feature_names, raw_prices=raw_prices)
    feature_names = list(model_artifacts["feature_names"])
    threshold = float(model_artifacts["threshold"])
    train_frame = model_artifacts["train_frame"]

    latest_live = live_features.iloc[[-1]].copy()
    latest_vector, raw_snapshot = score_latest_row(model_artifacts, feature_names, train_frame, latest_live)
    probability = float(predict_probabilities(model_artifacts, latest_vector)[0])
    execution_rule = get_live_execution_rule()

    historical_probabilities = build_history_probabilities(model_artifacts, splits, feature_names)
    execution_cutoff = resolve_execution_cutoff(execution_rule, float(threshold), historical_probabilities)
    predicted_label = int(probability >= execution_cutoff)
    model_predicted_label = int(probability >= threshold)
    raw_signal, band_info = classify_signal(probability, float(execution_cutoff), historical_probabilities)
    model_signal, model_band_info = classify_signal(probability, float(threshold), historical_probabilities)
    signal, buy_point_summary = apply_buy_point_overlay(raw_signal, raw_snapshot, asset_key=asset_key)
    rule_top_pct = get_rule_top_pct()
    rule_summary = summarize_rule(probability, historical_probabilities, rule_top_pct)
    model_rationale = build_model_rationale(raw_snapshot)
    rule_rationale = build_rule_rationale(probability, float(threshold), rule_summary)
    bullish = predicted_label == 1
    live_operator_line_id = resolve_live_operator_line_id(feature_names, str(model_artifacts["model_family"]))
    live_provenance = build_live_provenance(model_artifacts, live_operator_line_id)

    live_decision_rule = "threshold_plus_buy_point_overlay"
    if asset_key == "gld" and uses_gld_term_panic_overlay(live_operator_line_id, str(model_artifacts["model_family"])):
        live_decision_rule = "threshold_plus_buy_point_overlay_plus_vix_vxv_term_panic_block"

    output = {
        "signal_summary": {
            "signal": signal,
            "verdict": "模型偏向中期進場" if bullish else "模型目前不偏向中期進場",
            "predicted_label": predicted_label,
            "predicted_probability": round(probability, 4),
            "decision_threshold": round(float(execution_cutoff), 4),
            "raw_model_signal": raw_signal,
            "execution_rule": execution_rule,
            **band_info,
        },
        "model_signal_summary": {
            "signal": model_signal,
            "verdict": "模型偏向中期進場" if bullish else "模型目前不偏向中期進場",
            "predicted_label": model_predicted_label,
            "predicted_probability": round(probability, 4),
            "decision_threshold": round(float(threshold), 4),
            **model_band_info,
        },
        "buy_point_summary": buy_point_summary,
        "rule_summary": rule_summary,
        "rationale_summary": {
            "model_reasons": model_rationale,
            "rule_reason": rule_rationale,
        },
        "asset_key": asset_key,
        "symbol": ac.get_asset_symbol(),
        "latest_raw_date": latest_live["date"].iloc[0].strftime("%Y-%m-%d"),
        "latest_open": round(float(latest_live["open"].iloc[0]), 2),
        "latest_high": round(float(latest_live["high"].iloc[0]), 2),
        "latest_low": round(float(latest_live["low"].iloc[0]), 2),
        "latest_close": round(float(latest_live["close"].iloc[0]), 2),
        "trained_until_label_date": str(
            model_artifacts.get("trained_until_label_date", splits["test"].frame["date"].iloc[-1].strftime("%Y-%m-%d"))
        ),
        "model_summary": {
            "model_family": str(model_artifacts["model_family"]),
            "label_mode": str(model_artifacts.get("live_label_mode", get_live_label_mode())),
            "model_extra_features": [name for name in feature_names if name not in tr.FEATURE_COLUMNS],
            "threshold_metric": str(model_artifacts.get("threshold_metric", get_live_threshold_metric())),
            "default_interactions": list(model_artifacts.get("default_interactions", [])),
            "live_decision_rule": live_decision_rule,
            "live_execution_rule": execution_rule,
            "reference_percentile_rule": f"top_{rule_top_pct:g}pct",
            "xgboost_params": model_artifacts.get("xgboost_params", {}),
        },
        "model_extra_features": [name for name in feature_names if name not in tr.FEATURE_COLUMNS],
        "latest_feature_snapshot": {
            key: round(value, 4)
            for key, value in raw_snapshot.items()
            if key in {"ret_20", "ret_60", "drawdown_20", "volume_vs_20", "rsi_14", "sma_gap_20", "sma_gap_60"}
        },
    }
    if live_operator_line_id:
        output["live_operator_line_id"] = live_operator_line_id
    if live_provenance:
        output["live_provenance"] = live_provenance
    latest_prediction_path = Path(ac.get_latest_prediction_path())
    latest_prediction_path.parent.mkdir(parents=True, exist_ok=True)
    latest_prediction_path.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(output, indent=2, ensure_ascii=False))


def build_live_analysis_context() -> dict[str, Any]:
    tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
    asset_key = str(ac.load_asset_config()["asset_key"])
    raw_prices = download_asset_prices()
    live_features = add_context_features(add_relative_strength_features(add_price_features(raw_prices), BENCHMARK_SYMBOL))
    splits = tr.load_splits()
    feature_names = build_feature_names()
    needs_vix_features = any(name.startswith("vix_") for name in feature_names)
    needs_gld_term_panic = active_gld_term_panic_overlay(asset_key)
    vix_frame = None
    if needs_vix_features or needs_gld_term_panic:
        vix_frame = download_vix_prices()
    if needs_vix_features and vix_frame is not None:
        live_features = add_vix_features(live_features, vix_frame)
    if needs_gld_term_panic:
        if vix_frame is None:
            vix_frame = download_vix_prices()
        live_features = add_vix_features(live_features, vix_frame)
        live_features = add_vix_term_structure_features(live_features, download_vix3m_prices())
    model_artifacts = fit_model(splits, feature_names, raw_prices=raw_prices)
    feature_names = list(model_artifacts["feature_names"])
    threshold = float(model_artifacts["threshold"])
    train_frame = model_artifacts["train_frame"]
    historical_probabilities = build_history_probabilities(model_artifacts, splits, feature_names)
    return {
        "asset_key": asset_key,
        "live_features": live_features,
        "splits": splits,
        "feature_names": feature_names,
        "model_artifacts": model_artifacts,
        "threshold": threshold,
        "train_frame": train_frame,
        "historical_probabilities": historical_probabilities,
        "rule_top_pct": get_rule_top_pct(),
    }


def build_latest_prediction_output(context: Mapping[str, Any]) -> dict[str, object]:
    asset_key = str(context["asset_key"])
    live_features = context["live_features"]
    splits = cast(Mapping[str, DatasetSplit], context["splits"])
    feature_names = list(cast(list[str], context["feature_names"]))
    model_artifacts = cast(dict[str, Any], context["model_artifacts"])
    threshold = float(context["threshold"])
    train_frame = context["train_frame"]
    historical_probabilities = np.asarray(context["historical_probabilities"], dtype=np.float32)
    rule_top_pct = float(context["rule_top_pct"])

    latest_live = live_features.iloc[[-1]].copy()
    latest_vector, raw_snapshot = score_latest_row(model_artifacts, feature_names, train_frame, latest_live)
    probability = float(predict_probabilities(model_artifacts, latest_vector)[0])
    execution_rule = get_live_execution_rule()
    execution_cutoff = resolve_execution_cutoff(execution_rule, float(threshold), historical_probabilities)
    predicted_label = int(probability >= execution_cutoff)
    model_predicted_label = int(probability >= threshold)
    raw_signal, band_info = classify_signal(probability, float(execution_cutoff), historical_probabilities)
    model_signal, model_band_info = classify_signal(probability, float(threshold), historical_probabilities)
    signal, buy_point_summary = apply_buy_point_overlay(raw_signal, raw_snapshot, asset_key=asset_key)
    rule_summary = summarize_rule(probability, historical_probabilities, rule_top_pct)
    model_rationale = build_model_rationale(raw_snapshot)
    rule_rationale = build_rule_rationale(probability, float(threshold), rule_summary)
    live_operator_line_id = resolve_live_operator_line_id(feature_names, str(model_artifacts["model_family"]))
    live_provenance = build_live_provenance(model_artifacts, live_operator_line_id)

    live_decision_rule = "threshold_plus_buy_point_overlay"
    if asset_key == "gld" and uses_gld_term_panic_overlay(live_operator_line_id, str(model_artifacts["model_family"])):
        live_decision_rule = "threshold_plus_buy_point_overlay_plus_vix_vxv_term_panic_block"

    output: dict[str, object] = {
        "signal_summary": {
            "signal": signal,
            "verdict": "模型偏向中期進場" if predicted_label == 1 else "模型目前不偏向中期進場",
            "predicted_label": predicted_label,
            "predicted_probability": round(probability, 4),
            "decision_threshold": round(float(execution_cutoff), 4),
            "raw_model_signal": raw_signal,
            "execution_rule": execution_rule,
            **band_info,
        },
        "model_signal_summary": {
            "signal": model_signal,
            "verdict": "模型偏向中期進場" if model_predicted_label == 1 else "模型目前不偏向中期進場",
            "predicted_label": model_predicted_label,
            "predicted_probability": round(probability, 4),
            "decision_threshold": round(float(threshold), 4),
            **model_band_info,
        },
        "buy_point_summary": buy_point_summary,
        "rule_summary": rule_summary,
        "rationale_summary": {
            "model_reasons": model_rationale,
            "rule_reason": rule_rationale,
        },
        "asset_key": asset_key,
        "symbol": ac.get_asset_symbol(),
        "latest_raw_date": latest_live["date"].iloc[0].strftime("%Y-%m-%d"),
        "latest_open": round(float(latest_live["open"].iloc[0]), 2),
        "latest_high": round(float(latest_live["high"].iloc[0]), 2),
        "latest_low": round(float(latest_live["low"].iloc[0]), 2),
        "latest_close": round(float(latest_live["close"].iloc[0]), 2),
        "trained_until_label_date": str(
            model_artifacts.get("trained_until_label_date", splits["test"].frame["date"].iloc[-1].strftime("%Y-%m-%d"))
        ),
        "model_summary": {
            "model_family": str(model_artifacts["model_family"]),
            "label_mode": str(model_artifacts.get("live_label_mode", get_live_label_mode())),
            "model_extra_features": [name for name in feature_names if name not in tr.FEATURE_COLUMNS],
            "threshold_metric": str(model_artifacts.get("threshold_metric", get_live_threshold_metric())),
            "default_interactions": list(model_artifacts.get("default_interactions", [])),
            "live_decision_rule": live_decision_rule,
            "live_execution_rule": execution_rule,
            "reference_percentile_rule": f"top_{rule_top_pct:g}pct",
            "xgboost_params": model_artifacts.get("xgboost_params", {}),
        },
        "model_extra_features": [name for name in feature_names if name not in tr.FEATURE_COLUMNS],
        "latest_feature_snapshot": {
            key: round(value, 4)
            for key, value in raw_snapshot.items()
            if key in {"ret_20", "ret_60", "drawdown_20", "volume_vs_20", "rsi_14", "sma_gap_20", "sma_gap_60"}
        },
    }
    if live_operator_line_id:
        output["live_operator_line_id"] = live_operator_line_id
    if live_provenance:
        output["live_provenance"] = live_provenance
    return output


def write_latest_prediction_output(output: Mapping[str, object]) -> None:
    latest_prediction_path = Path(ac.get_latest_prediction_path())
    latest_prediction_path.parent.mkdir(parents=True, exist_ok=True)
    latest_prediction_path.write_text(json.dumps(dict(output), indent=2, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    main()
