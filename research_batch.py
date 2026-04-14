"""
Run a batch of formal asset research comparisons and export compact summaries.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
import importlib
from typing import TypedDict, cast

import numpy as np
import pandas as pd

import asset_config as ac
import predict_latest as live
import prepare as pr
import train as tr

CACHE_DIR = str(ac.get_cache_dir())
BACKTEST_OUTPUT_PATH = str(ac.get_backtest_output_path())
REGIME_OUTPUT_PATH = str(ac.get_regime_output_path())
SIGNAL_OUTPUT_PATH = str(ac.get_signal_output_path())
FORWARD_OUTPUT_PATH = str(ac.get_forward_output_path())
RULE_OUTPUT_PATH = str(ac.get_rule_output_path())
ROUND_OUTPUT_PATH = str(ac.get_research_batch_path())
FUTURE_RETURN_COLUMN = "future_return_60"
DEFAULT_INTERACTIONS = (("drawdown_20", "volume_vs_20"),)
HEADLINE_SCORE_WEIGHTS = {
    "validation_f1": 0.20,
    "validation_bal_acc": 0.10,
    "test_f1": 0.40,
    "test_bal_acc": 0.30,
}
VALIDATION_BAL_ACC_GATE = 0.52
TEST_BAL_ACC_GATE = 0.54

try:
    _XGBOOST_MODULE = importlib.import_module("xgboost")
    _XGBOOST_IMPORT_ERROR: Exception | None = None
except Exception as exc:  # pragma: no cover - exercised through require_xgboost tests
    _XGBOOST_MODULE = None
    _XGBOOST_IMPORT_ERROR = exc


@dataclass
class ModelResult:
    name: str
    feature_names: list[str]
    threshold: float
    validation_f1: float
    validation_accuracy: float
    validation_bal_acc: float
    validation_positive_rate: float
    test_f1: float
    test_accuracy: float
    test_bal_acc: float
    test_positive_rate: float
    test_avg_return: float
    validation_rows: int
    test_rows: int


@dataclass
class ForwardFoldResult:
    fold_name: str
    validation_f1: float
    validation_bal_acc: float
    test_f1: float
    test_bal_acc: float
    test_positive_rate: float


@dataclass
class BacktestResult:
    model_name: str
    rule_name: str
    selected_count: int
    hit_rate: float
    avg_return: float
    max_drawdown_simple: float
    max_drawdown_compound: float
    longest_win_streak: int
    longest_loss_streak: int
    threshold_or_cutoff: float


class FamilyArtifacts(TypedDict):
    model_family: str
    weights: np.ndarray | None
    negative_weights: np.ndarray | None
    positive_weights: np.ndarray | None
    gate_feature: str | None
    threshold: float
    validation_y: np.ndarray
    test_y: np.ndarray
    validation_logits: np.ndarray
    test_logits: np.ndarray
    validation_probabilities: np.ndarray
    test_probabilities: np.ndarray
    validation_metrics: tr.Metrics
    test_metrics: tr.Metrics


class ModelArtifacts(TypedDict):
    model_family: str
    feature_names: list[str]
    pair_indices: tuple[tuple[int, int], ...]
    weights: np.ndarray | None
    negative_weights: np.ndarray | None
    positive_weights: np.ndarray | None
    threshold: float
    train_mean: np.ndarray
    train_std: np.ndarray
    clean_splits: dict[str, pd.DataFrame]
    validation_probabilities: np.ndarray
    test_probabilities: np.ndarray
    validation_y: np.ndarray
    test_y: np.ndarray
    neg_weight: float
    gate_feature: str | None


def require_xgboost():
    global _XGBOOST_MODULE, _XGBOOST_IMPORT_ERROR
    if _XGBOOST_MODULE is not None:
        return _XGBOOST_MODULE
    try:
        _XGBOOST_MODULE = importlib.import_module("xgboost")
        _XGBOOST_IMPORT_ERROR = None
        return _XGBOOST_MODULE
    except Exception as exc:  # pragma: no cover - exercised through require_xgboost tests
        _XGBOOST_IMPORT_ERROR = exc
    message = "xgboost is required for XGBoost research runs. Install the 'xgboost' package first."
    if _XGBOOST_IMPORT_ERROR is not None:
        raise ModuleNotFoundError(message) from _XGBOOST_IMPORT_ERROR
    raise ModuleNotFoundError(message)


def classify_probs_by_rule(probabilities: np.ndarray, threshold: float, rule_name: str) -> tuple[np.ndarray, float]:
    if rule_name == "threshold":
        return probabilities >= threshold, threshold
    if rule_name.startswith("top_") and rule_name.endswith("pct"):
        raw_pct = rule_name[len("top_") : -len("pct")].replace("_", ".")
        pct = float(raw_pct)
        cutoff = float(np.quantile(probabilities, 1.0 - pct / 100.0))
        return probabilities >= cutoff, cutoff
    if rule_name.startswith("fixed_"):
        cutoff = float(rule_name.split("_", 1)[1])
        return probabilities >= cutoff, cutoff
    raise ValueError(f"Unsupported rule: {rule_name}")


def compute_headline_score(
    validation_f1: float,
    validation_bal_acc: float,
    test_f1: float,
    test_bal_acc: float,
) -> float:
    return (
        HEADLINE_SCORE_WEIGHTS["validation_f1"] * validation_f1
        + HEADLINE_SCORE_WEIGHTS["validation_bal_acc"] * validation_bal_acc
        + HEADLINE_SCORE_WEIGHTS["test_f1"] * test_f1
        + HEADLINE_SCORE_WEIGHTS["test_bal_acc"] * test_bal_acc
    )


def passes_promotion_gate(validation_bal_acc: float, test_bal_acc: float) -> bool:
    return validation_bal_acc >= VALIDATION_BAL_ACC_GATE and test_bal_acc >= TEST_BAL_ACC_GATE


def ensure_cache_dir() -> None:
    os.makedirs(CACHE_DIR, exist_ok=True)


def add_regime_features(frame: pd.DataFrame) -> pd.DataFrame:
    df = frame.copy()
    df["year"] = df["date"].dt.year.astype(float)
    df["rolling_return_120"] = df["close"].pct_change(120)
    df["rolling_vol_60"] = df["ret_1"].rolling(60).std()
    df["ret_120"] = df["close"].pct_change(120)
    df["sma_gap_120"] = df["close"] / df["close"].rolling(120).mean() - 1.0
    df["drawdown_120"] = (df["close"] - df["close"].rolling(120).max()) / df["close"].rolling(120).max()
    volume = df["volume"].replace(0, np.nan)
    df["volume_vs_120"] = volume / volume.rolling(120).mean() - 1.0
    return df


def build_labeled_frame(
    raw: pd.DataFrame,
    horizon_days: int = 60,
    upper_barrier: float = 0.08,
    lower_barrier: float = -0.04,
    label_mode: str = "drop-neutral",
) -> pd.DataFrame:
    df = pr.add_price_features(raw)
    df = pr.add_relative_strength_features(df, pr.BENCHMARK_SYMBOL)
    df = pr.add_context_features(df)
    df = add_regime_features(df)
    labels, realized_returns = pr.build_barrier_labels(df, horizon_days, upper_barrier, lower_barrier)
    train_end, _ = pr.split_indices(len(df))
    labels = pr.apply_label_mode(labels, realized_returns, label_mode, train_end=train_end)
    df[pr.TARGET_COLUMN] = labels
    df[FUTURE_RETURN_COLUMN] = realized_returns
    selectable_experimental = [name for name in pr.EXPERIMENTAL_FEATURE_COLUMNS if name in df.columns]
    needed = pr.FEATURE_COLUMNS + selectable_experimental + [FUTURE_RETURN_COLUMN]
    if label_mode != "keep-all-binary":
        needed.append(pr.TARGET_COLUMN)
    df = df.replace([np.inf, -np.inf], np.nan)
    return df.dropna(subset=needed).reset_index(drop=True)


def get_feature_names(extra_features: tuple[str, ...] = (), drop_features: tuple[str, ...] = ()) -> list[str]:
    feature_names = list(pr.FEATURE_COLUMNS)
    for name in extra_features:
        if name not in feature_names:
            feature_names.append(name)
    return [name for name in feature_names if name not in set(drop_features)]


def split_frame(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    train_end, valid_end = pr.split_indices(len(frame))
    return {
        "train": frame.iloc[:train_end].copy().reset_index(drop=True),
        "validation": frame.iloc[train_end:valid_end].copy().reset_index(drop=True),
        "test": frame.iloc[valid_end:].copy().reset_index(drop=True),
    }


def active_interaction_pairs(
    feature_names: list[str], extra_interactions: tuple[tuple[str, str], ...] = ()
) -> tuple[tuple[int, int], ...]:
    pairs = list(DEFAULT_INTERACTIONS)
    for pair in extra_interactions:
        if pair not in pairs:
            pairs.append(pair)
    index = {name: idx for idx, name in enumerate(feature_names)}
    return tuple((index[left], index[right]) for left, right in pairs if left in index and right in index)


def standardize_from_train(
    train_x: np.ndarray, validation_x: np.ndarray, test_x: np.ndarray
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    return (train_x - mean) / std, (validation_x - mean) / std, (test_x - mean) / std, mean, std


def add_interactions(features: np.ndarray, pairs: tuple[tuple[int, int], ...]) -> np.ndarray:
    if not pairs:
        return features
    extras = [features[:, i : i + 1] * features[:, j : j + 1] for i, j in pairs]
    return np.concatenate([features] + extras, axis=1)


def prepare_feature_matrices(
    splits: dict[str, pd.DataFrame], feature_names: list[str], extra_interactions: tuple[tuple[str, str], ...] = ()
) -> tuple[dict[str, pd.DataFrame], dict[str, np.ndarray], np.ndarray, np.ndarray, tuple[tuple[int, int], ...]]:
    clean_splits: dict[str, pd.DataFrame] = {}
    for split_name, frame in splits.items():
        clean_splits[split_name] = frame.dropna(subset=feature_names + [pr.TARGET_COLUMN, FUTURE_RETURN_COLUMN]).reset_index(drop=True)
    matrices = {
        split_name: clean_splits[split_name][feature_names].to_numpy(dtype=np.float32)
        for split_name in ("train", "validation", "test")
    }
    train_x, validation_x, test_x, mean, std = standardize_from_train(
        matrices["train"], matrices["validation"], matrices["test"]
    )
    pair_indices = active_interaction_pairs(feature_names, extra_interactions)
    train_x = add_interactions(train_x, pair_indices)
    validation_x = add_interactions(validation_x, pair_indices)
    test_x = add_interactions(test_x, pair_indices)
    return (
        clean_splits,
        {
            "train": tr.add_bias(train_x),
            "validation": tr.add_bias(validation_x),
            "test": tr.add_bias(test_x),
        },
        mean,
        std,
        pair_indices,
    )


def prepare_tree_feature_matrices(
    splits: dict[str, pd.DataFrame], feature_names: list[str]
) -> tuple[dict[str, pd.DataFrame], dict[str, np.ndarray]]:
    clean_splits: dict[str, pd.DataFrame] = {}
    for split_name, frame in splits.items():
        clean_splits[split_name] = frame.dropna(subset=feature_names + [pr.TARGET_COLUMN, FUTURE_RETURN_COLUMN]).reset_index(drop=True)
    matrices = {
        split_name: clean_splits[split_name][feature_names].to_numpy(dtype=np.float32)
        for split_name in ("train", "validation", "test")
    }
    return clean_splits, matrices


def probabilities_to_logits(probabilities: np.ndarray) -> np.ndarray:
    clipped = np.clip(np.asarray(probabilities, dtype=np.float32), 1e-6, 1.0 - 1e-6)
    return np.log(clipped / (1.0 - clipped))


def fit_logistic_weights(
    train_x: np.ndarray,
    train_y: np.ndarray,
    validation_x: np.ndarray,
    validation_y: np.ndarray,
    validation_returns: np.ndarray,
    neg_weight: float,
    threshold_steps: int,
) -> tuple[np.ndarray, float]:
    weights = np.zeros(train_x.shape[1], dtype=np.float32)
    best_weights = weights.copy()
    best_validation_f1 = -np.inf
    best_threshold = 0.5
    epochs_without_improvement = 0

    for _epoch in range(1, tr.MAX_EPOCHS + 1):
        logits = train_x @ weights
        probs = tr.sigmoid(logits)
        sample_weights = np.where(train_y == 1.0, tr.POS_WEIGHT, neg_weight).astype(np.float32)
        gradient = train_x.T @ ((probs - train_y) * sample_weights) / train_x.shape[0]
        gradient[:-1] += tr.L2_REG * weights[:-1]
        weights -= tr.LEARNING_RATE * gradient

        validation_logits = validation_x @ weights
        threshold = select_threshold_with_steps(tr.sigmoid(validation_logits), validation_y, threshold_steps)
        validation_metrics = tr.compute_metrics(validation_logits, validation_y, validation_returns, threshold)
        if validation_metrics.f1 > best_validation_f1:
            best_validation_f1 = validation_metrics.f1
            best_weights = weights.copy()
            best_threshold = threshold
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= tr.PATIENCE:
            break

    return best_weights, best_threshold


def train_logistic_family(
    clean_splits: dict[str, pd.DataFrame],
    matrices: dict[str, np.ndarray],
    neg_weight: float,
    threshold_steps: int,
) -> FamilyArtifacts:
    train_x = matrices["train"]
    validation_x = matrices["validation"]
    test_x = matrices["test"]
    train_y = clean_splits["train"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_y = clean_splits["validation"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    test_y = clean_splits["test"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_returns = clean_splits["validation"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)
    test_returns = clean_splits["test"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)

    best_weights, best_threshold = fit_logistic_weights(
        train_x,
        train_y,
        validation_x,
        validation_y,
        validation_returns,
        neg_weight,
        threshold_steps,
    )
    validation_logits = validation_x @ best_weights
    test_logits = test_x @ best_weights
    validation_probabilities = tr.sigmoid(validation_logits)
    test_probabilities = tr.sigmoid(test_logits)
    return {
        "model_family": "logistic",
        "weights": best_weights,
        "negative_weights": None,
        "positive_weights": None,
        "gate_feature": None,
        "threshold": best_threshold,
        "validation_y": validation_y,
        "test_y": test_y,
        "validation_logits": validation_logits,
        "test_logits": test_logits,
        "validation_probabilities": validation_probabilities,
        "test_probabilities": test_probabilities,
        "validation_metrics": tr.compute_metrics(validation_logits, validation_y, validation_returns, best_threshold),
        "test_metrics": tr.compute_metrics(test_logits, test_y, test_returns, best_threshold),
    }


def regime_gate_mask(frame: pd.DataFrame, gate_feature: str, positive_regime: bool) -> np.ndarray:
    values = frame[gate_feature].to_numpy(dtype=np.float32)
    if positive_regime:
        return values >= 0.5
    return values < 0.5


def can_fit_regime(mask: np.ndarray, labels: np.ndarray) -> bool:
    if int(mask.sum()) < 12:
        return False
    subset = labels[mask]
    return len(np.unique(subset)) >= 2


def combine_regime_probabilities(
    matrices: dict[str, np.ndarray],
    clean_splits: dict[str, pd.DataFrame],
    gate_feature: str,
    negative_weights: np.ndarray,
    positive_weights: np.ndarray,
) -> dict[str, np.ndarray]:
    combined: dict[str, np.ndarray] = {}
    for split_name in ("validation", "test"):
        positive_mask = regime_gate_mask(clean_splits[split_name], gate_feature, positive_regime=True)
        logits = np.empty(len(clean_splits[split_name]), dtype=np.float32)
        logits[positive_mask] = matrices[split_name][positive_mask] @ positive_weights
        logits[~positive_mask] = matrices[split_name][~positive_mask] @ negative_weights
        combined[split_name] = tr.sigmoid(logits)
    return combined


def train_regime_dual_logistic_family(
    clean_splits: dict[str, pd.DataFrame],
    matrices: dict[str, np.ndarray],
    neg_weight: float,
    threshold_steps: int,
    gate_feature: str,
) -> FamilyArtifacts:
    train_y = clean_splits["train"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_y = clean_splits["validation"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    test_y = clean_splits["test"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_returns = clean_splits["validation"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)
    test_returns = clean_splits["test"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32)

    pooled = train_logistic_family(clean_splits, matrices, neg_weight, threshold_steps)
    negative_weights = pooled["weights"]
    positive_weights = pooled["weights"]

    train_positive_mask = regime_gate_mask(clean_splits["train"], gate_feature, positive_regime=True)
    validation_positive_mask = regime_gate_mask(clean_splits["validation"], gate_feature, positive_regime=True)
    if can_fit_regime(~train_positive_mask, train_y) and can_fit_regime(~validation_positive_mask, validation_y):
        negative_weights, _ = fit_logistic_weights(
            matrices["train"][~train_positive_mask],
            train_y[~train_positive_mask],
            matrices["validation"][~validation_positive_mask],
            validation_y[~validation_positive_mask],
            validation_returns[~validation_positive_mask],
            neg_weight,
            threshold_steps,
        )
    if can_fit_regime(train_positive_mask, train_y) and can_fit_regime(validation_positive_mask, validation_y):
        positive_weights, _ = fit_logistic_weights(
            matrices["train"][train_positive_mask],
            train_y[train_positive_mask],
            matrices["validation"][validation_positive_mask],
            validation_y[validation_positive_mask],
            validation_returns[validation_positive_mask],
            neg_weight,
            threshold_steps,
        )

    combined_probabilities = combine_regime_probabilities(
        matrices,
        clean_splits,
        gate_feature,
        negative_weights,
        positive_weights,
    )
    threshold = select_threshold_with_steps(combined_probabilities["validation"], validation_y, threshold_steps)
    validation_logits = probabilities_to_logits(combined_probabilities["validation"])
    test_logits = probabilities_to_logits(combined_probabilities["test"])
    return {
        "model_family": "regime_dual_logistic",
        "weights": None,
        "gate_feature": gate_feature,
        "negative_weights": negative_weights,
        "positive_weights": positive_weights,
        "threshold": threshold,
        "validation_y": validation_y,
        "test_y": test_y,
        "validation_logits": validation_logits,
        "test_logits": test_logits,
        "validation_probabilities": combined_probabilities["validation"],
        "test_probabilities": combined_probabilities["test"],
        "validation_metrics": tr.compute_metrics(validation_logits, validation_y, validation_returns, threshold),
        "test_metrics": tr.compute_metrics(test_logits, test_y, test_returns, threshold),
    }


def train_model(
    frame: pd.DataFrame,
    name: str,
    extra_features: tuple[str, ...] = (),
    drop_features: tuple[str, ...] = (),
    extra_interactions: tuple[tuple[str, str], ...] = (),
    neg_weight: float | None = None,
    threshold_steps: int | None = None,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> tuple[ModelResult, ModelArtifacts]:
    feature_names = get_feature_names(extra_features, drop_features)
    splits = split_frame(frame)
    clean_splits, matrices, mean, std, pair_indices = prepare_feature_matrices(splits, feature_names, extra_interactions)
    neg_weight = tr.NEG_WEIGHT if neg_weight is None else neg_weight
    threshold_steps = tr.THRESHOLD_STEPS if threshold_steps is None else threshold_steps
    if model_family == "logistic":
        family_artifacts = train_logistic_family(clean_splits, matrices, neg_weight, threshold_steps)
    elif model_family == "regime_dual_logistic":
        family_artifacts = train_regime_dual_logistic_family(clean_splits, matrices, neg_weight, threshold_steps, gate_feature)
    else:
        raise ValueError(f"Unsupported model family: {model_family}")

    validation_metrics = cast(tr.Metrics, family_artifacts["validation_metrics"])
    test_metrics = cast(tr.Metrics, family_artifacts["test_metrics"])
    threshold_value = cast(float, family_artifacts["threshold"])
    result = ModelResult(
        name=name,
        feature_names=feature_names,
        threshold=float(threshold_value),
        validation_f1=validation_metrics.f1,
        validation_accuracy=validation_metrics.accuracy,
        validation_bal_acc=validation_metrics.balanced_accuracy,
        validation_positive_rate=validation_metrics.positive_rate,
        test_f1=test_metrics.f1,
        test_accuracy=test_metrics.accuracy,
        test_bal_acc=test_metrics.balanced_accuracy,
        test_positive_rate=test_metrics.positive_rate,
        test_avg_return=test_metrics.avg_realized_return,
        validation_rows=len(clean_splits["validation"]),
        test_rows=len(clean_splits["test"]),
    )
    artifacts: ModelArtifacts = {
        "model_family": model_family,
        "feature_names": feature_names,
        "pair_indices": pair_indices,
        "weights": cast(np.ndarray, family_artifacts.get("weights")) if family_artifacts.get("weights") is not None else None,
        "threshold": float(threshold_value),
        "train_mean": mean,
        "train_std": std,
        "clean_splits": clean_splits,
        "test_probabilities": cast(np.ndarray, family_artifacts["test_probabilities"]),
        "validation_probabilities": cast(np.ndarray, family_artifacts["validation_probabilities"]),
        "neg_weight": neg_weight,
        "gate_feature": cast(str, family_artifacts.get("gate_feature")) if family_artifacts.get("gate_feature") is not None else None,
        "negative_weights": cast(np.ndarray, family_artifacts.get("negative_weights")) if family_artifacts.get("negative_weights") is not None else None,
        "positive_weights": cast(np.ndarray, family_artifacts.get("positive_weights")) if family_artifacts.get("positive_weights") is not None else None,
    }
    return result, artifacts


def train_xgboost_model(
    frame: pd.DataFrame,
    name: str,
    extra_features: tuple[str, ...] = (),
    drop_features: tuple[str, ...] = (),
    neg_weight: float | None = None,
    n_estimators: int = 200,
    max_depth: int = 3,
    learning_rate: float = 0.05,
) -> tuple[ModelResult, dict[str, object]]:
    xgb = require_xgboost()
    feature_names = get_feature_names(extra_features, drop_features)
    splits = split_frame(frame)
    clean_splits, matrices = prepare_tree_feature_matrices(splits, feature_names)
    train_x = matrices["train"]
    validation_x = matrices["validation"]
    test_x = matrices["test"]
    train_y = clean_splits["train"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_y = clean_splits["validation"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    test_y = clean_splits["test"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32)

    neg_weight = tr.NEG_WEIGHT if neg_weight is None else neg_weight
    sample_weights = np.where(train_y == 1.0, tr.POS_WEIGHT, neg_weight).astype(np.float32)
    if hasattr(xgb, "DMatrix") and hasattr(xgb, "train"):
        train_matrix = xgb.DMatrix(train_x, label=train_y, weight=sample_weights)
        validation_matrix = xgb.DMatrix(validation_x, label=validation_y)
        test_matrix = xgb.DMatrix(test_x, label=test_y)
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
        test_probabilities = np.asarray(model.predict(test_matrix), dtype=np.float32)
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
        model.fit(train_x, train_y, sample_weight=sample_weights)
        validation_probabilities = np.asarray(model.predict_proba(validation_x)[:, 1], dtype=np.float32)
        test_probabilities = np.asarray(model.predict_proba(test_x)[:, 1], dtype=np.float32)
    threshold = select_threshold_with_steps(validation_probabilities, validation_y, tr.THRESHOLD_STEPS)
    validation_logits = np.log(validation_probabilities / np.clip(1.0 - validation_probabilities, 1e-6, None))
    test_logits = np.log(test_probabilities / np.clip(1.0 - test_probabilities, 1e-6, None))
    validation_metrics = tr.compute_metrics(
        validation_logits,
        validation_y,
        clean_splits["validation"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        threshold,
    )
    test_metrics = tr.compute_metrics(
        test_logits,
        test_y,
        clean_splits["test"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        threshold,
    )
    result = ModelResult(
        name=name,
        feature_names=feature_names,
        threshold=threshold,
        validation_f1=validation_metrics.f1,
        validation_accuracy=validation_metrics.accuracy,
        validation_bal_acc=validation_metrics.balanced_accuracy,
        validation_positive_rate=validation_metrics.positive_rate,
        test_f1=test_metrics.f1,
        test_accuracy=test_metrics.accuracy,
        test_bal_acc=test_metrics.balanced_accuracy,
        test_positive_rate=test_metrics.positive_rate,
        test_avg_return=test_metrics.avg_realized_return,
        validation_rows=len(clean_splits["validation"]),
        test_rows=len(clean_splits["test"]),
    )
    artifacts = {
        "model_family": "xgboost",
        "feature_names": feature_names,
        "model": model,
        "threshold": threshold,
        "clean_splits": clean_splits,
        "validation_probabilities": validation_probabilities,
        "test_probabilities": test_probabilities,
        "neg_weight": neg_weight,
    }
    return result, artifacts


def select_threshold_with_steps(probabilities: np.ndarray, labels: np.ndarray, threshold_steps: int) -> float:
    thresholds = np.linspace(tr.THRESHOLD_MIN, tr.THRESHOLD_MAX, threshold_steps)
    return tr.select_threshold_from_grid(
        probabilities,
        labels,
        thresholds,
        target_positive_rate=tr.get_env_optional_float("AR_THRESHOLD_TARGET_POSITIVE_RATE"),
        positive_rate_penalty=tr.get_env_float("AR_THRESHOLD_POSITIVE_RATE_PENALTY", 0.0),
        max_positive_rate=tr.get_env_float("AR_THRESHOLD_MAX_POSITIVE_RATE", 1.0),
    )


def longest_streak(returns: np.ndarray, positive: bool) -> int:
    best = 0
    current = 0
    for value in returns:
        condition = value > 0 if positive else value <= 0
        if condition:
            current += 1
            best = max(best, current)
        else:
            current = 0
    return best


def max_drawdown(equity_curve: np.ndarray) -> float:
    peaks = np.maximum.accumulate(equity_curve)
    drawdowns = equity_curve / np.maximum(peaks, 1e-8) - 1.0
    return float(drawdowns.min()) if len(drawdowns) else 0.0


def run_non_overlap_backtest(
    dates: pd.Series, future_returns: np.ndarray, selected: np.ndarray, horizon_days: int, threshold_or_cutoff: float
) -> BacktestResult:
    chosen_returns: list[float] = []
    idx = 0
    while idx < len(selected):
        if selected[idx]:
            chosen_returns.append(float(future_returns[idx]))
            idx += horizon_days
        else:
            idx += 1
    returns = np.asarray(chosen_returns, dtype=np.float64)
    if len(returns) == 0:
        return BacktestResult("", "", 0, 0.0, 0.0, 0.0, 0.0, 0, 0, threshold_or_cutoff)
    simple_equity = np.cumsum(returns) + 1.0
    compound_equity = np.cumprod(1.0 + returns)
    return BacktestResult(
        model_name="",
        rule_name="",
        selected_count=len(returns),
        hit_rate=float((returns > 0).mean()),
        avg_return=float(returns.mean()),
        max_drawdown_simple=max_drawdown(simple_equity),
        max_drawdown_compound=max_drawdown(compound_equity),
        longest_win_streak=longest_streak(returns, positive=True),
        longest_loss_streak=longest_streak(returns, positive=False),
        threshold_or_cutoff=threshold_or_cutoff,
    )


def run_cooldown_backtest(
    future_returns: np.ndarray, selected: np.ndarray, cooldown_days: int, threshold_or_cutoff: float
) -> BacktestResult:
    chosen_returns: list[float] = []
    cooldown = 0
    for idx in range(len(selected)):
        if cooldown > 0:
            cooldown -= 1
            continue
        if selected[idx]:
            chosen_returns.append(float(future_returns[idx]))
            cooldown = cooldown_days
    returns = np.asarray(chosen_returns, dtype=np.float64)
    if len(returns) == 0:
        return BacktestResult("", "", 0, 0.0, 0.0, 0.0, 0.0, 0, 0, threshold_or_cutoff)
    simple_equity = np.cumsum(returns) + 1.0
    compound_equity = np.cumprod(1.0 + returns)
    return BacktestResult(
        model_name="",
        rule_name="",
        selected_count=len(returns),
        hit_rate=float((returns > 0).mean()),
        avg_return=float(returns.mean()),
        max_drawdown_simple=max_drawdown(simple_equity),
        max_drawdown_compound=max_drawdown(compound_equity),
        longest_win_streak=longest_streak(returns, positive=True),
        longest_loss_streak=longest_streak(returns, positive=False),
        threshold_or_cutoff=threshold_or_cutoff,
    )


def backtest_rules(model_name: str, artifacts: ModelArtifacts) -> list[BacktestResult]:
    clean_splits = cast(dict[str, pd.DataFrame], artifacts["clean_splits"])
    test_frame = clean_splits["test"]
    probs = np.asarray(cast(np.ndarray, artifacts["test_probabilities"]), dtype=np.float64)
    threshold = float(cast(float, artifacts["threshold"]))
    future_returns = test_frame[FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
    rows: list[BacktestResult] = []

    selections = {
        rule_name: classify_probs_by_rule(probs, threshold, rule_name)
        for rule_name in ("threshold", "top_10pct", "top_15pct", "top_20pct")
    }
    historical_probs = np.concatenate(
        [np.asarray(cast(np.ndarray, artifacts["validation_probabilities"]), dtype=np.float64), np.asarray(cast(np.ndarray, artifacts["test_probabilities"]), dtype=np.float64)]
    )
    bullish_plus = np.array(
        [
            live.classify_signal(float(prob), threshold, historical_probs)[0]
            in {"bullish", "strong_bullish", "very_strong_bullish"}
            for prob in probs
        ],
        dtype=bool,
    )
    selections["bullish_plus"] = (bullish_plus, threshold)
    strong_plus = np.array(
        [
            live.classify_signal(float(prob), threshold, historical_probs)[0]
            in {"strong_bullish", "very_strong_bullish"}
            for prob in probs
        ],
        dtype=bool,
    )
    selections["strong_bullish_plus"] = (strong_plus, threshold)

    for rule_name, (selected, cutoff) in selections.items():
        result = run_non_overlap_backtest(
            test_frame["date"], future_returns, selected.astype(bool), pr.HORIZON_DAYS, float(cutoff)
        )
        result.model_name = model_name
        result.rule_name = rule_name
        rows.append(result)
    return rows


def fixed_threshold_backtests(model_name: str, artifacts: ModelArtifacts, thresholds: tuple[float, ...]) -> list[BacktestResult]:
    clean_splits = cast(dict[str, pd.DataFrame], artifacts["clean_splits"])
    test_frame = clean_splits["test"]
    probs = np.asarray(cast(np.ndarray, artifacts["test_probabilities"]), dtype=np.float64)
    future_returns = test_frame[FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
    rows: list[BacktestResult] = []
    for threshold in thresholds:
        result = run_non_overlap_backtest(test_frame["date"], future_returns, probs >= threshold, pr.HORIZON_DAYS, threshold)
        result.model_name = model_name
        result.rule_name = f"fixed_{threshold:.2f}"
        rows.append(result)
    return rows


def rule_comparison_rows(model_name: str, artifacts: ModelArtifacts, rules: tuple[str, ...]) -> list[dict[str, object]]:
    clean_splits = cast(dict[str, pd.DataFrame], artifacts["clean_splits"])
    test_frame = clean_splits["test"]
    probs = np.asarray(cast(np.ndarray, artifacts["test_probabilities"]), dtype=np.float64)
    labels = test_frame[pr.TARGET_COLUMN].to_numpy(dtype=np.float32)
    future_returns = test_frame[FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
    rows: list[dict[str, object]] = []
    for rule_name in rules:
        selected, cutoff = classify_probs_by_rule(probs, float(cast(float, artifacts["threshold"])), rule_name)
        selected_float = selected.astype(np.float32)
        tp = float(np.sum((selected_float == 1.0) & (labels == 1.0)))
        fp = float(np.sum((selected_float == 1.0) & (labels == 0.0)))
        fn = float(np.sum((selected_float == 0.0) & (labels == 1.0)))
        precision = tp / max(tp + fp, 1.0)
        recall = tp / max(tp + fn, 1.0)
        backtest = run_non_overlap_backtest(
            test_frame["date"], future_returns, selected.astype(bool), pr.HORIZON_DAYS, float(cutoff)
        )
        rows.append(
            {
                "model_name": model_name,
                "rule_name": rule_name,
                "threshold_or_cutoff": round_float(cutoff),
                "selected_count": backtest.selected_count,
                "predicted_positive_rate": round_float(float(selected.mean())),
                "precision": round_float(float(precision)),
                "recall": round_float(float(recall)),
                "hit_rate": round_float(backtest.hit_rate),
                "avg_return": round_float(backtest.avg_return),
                "max_drawdown_compound": round_float(backtest.max_drawdown_compound),
            }
        )
    return rows


def cooldown_backtests(model_name: str, artifacts: ModelArtifacts, cooldown_days: tuple[int, ...]) -> list[BacktestResult]:
    clean_splits = cast(dict[str, pd.DataFrame], artifacts["clean_splits"])
    test_frame = clean_splits["test"]
    probs = np.asarray(cast(np.ndarray, artifacts["test_probabilities"]), dtype=np.float64)
    threshold = float(cast(float, artifacts["threshold"]))
    future_returns = test_frame[FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
    rows: list[BacktestResult] = []
    for cooldown in cooldown_days:
        result = run_cooldown_backtest(future_returns, probs >= threshold, cooldown, threshold)
        result.model_name = model_name
        result.rule_name = f"cooldown_{cooldown}d"
        rows.append(result)
    return rows


def precision_recall(probabilities: np.ndarray, labels: np.ndarray, threshold: float) -> dict[str, float]:
    tp, tn, fp, fn, predictions = tr.classification_stats(probabilities, labels, threshold)
    precision = tp / max(tp + fp, 1.0)
    recall = tp / max(tp + fn, 1.0)
    return {
        "predicted_positive_rate": float(predictions.mean()),
        "precision": float(precision),
        "recall": float(recall),
    }


def walk_forward_splits(frame: pd.DataFrame, folds: int = 3) -> list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]]:
    total = len(frame)
    fold_size = total // (folds + 2)
    splits: list[tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = []
    for fold_idx in range(folds):
        train_end = fold_size * (fold_idx + 2)
        validation_end = train_end + fold_size
        test_end = min(validation_end + fold_size, total)
        if test_end - validation_end < max(30, fold_size // 2):
            break
        train = frame.iloc[:train_end].copy().reset_index(drop=True)
        validation = frame.iloc[train_end:validation_end].copy().reset_index(drop=True)
        test = frame.iloc[validation_end:test_end].copy().reset_index(drop=True)
        splits.append((train, validation, test))
    return splits


def fit_on_custom_splits(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    feature_names: list[str],
    neg_weight: float = tr.NEG_WEIGHT,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> ForwardFoldResult:
    artifacts = train_custom_model(
        train_frame,
        validation_frame,
        test_frame,
        feature_names,
        neg_weight=neg_weight,
        model_family=model_family,
        gate_feature=gate_feature,
    )
    validation_metrics = tr.compute_metrics(
        probabilities_to_logits(np.asarray(artifacts["validation_probabilities"], dtype=np.float32)),
        np.asarray(artifacts["validation_y"], dtype=np.float32),
        artifacts["clean_splits"]["validation"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        float(artifacts["threshold"]),
    )
    test_metrics = tr.compute_metrics(
        probabilities_to_logits(np.asarray(artifacts["test_probabilities"], dtype=np.float32)),
        np.asarray(artifacts["test_y"], dtype=np.float32),
        artifacts["clean_splits"]["test"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float32),
        float(artifacts["threshold"]),
    )
    return ForwardFoldResult(
        fold_name="",
        validation_f1=validation_metrics.f1,
        validation_bal_acc=validation_metrics.balanced_accuracy,
        test_f1=test_metrics.f1,
        test_bal_acc=test_metrics.balanced_accuracy,
        test_positive_rate=test_metrics.positive_rate,
    )


def train_custom_model(
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    test_frame: pd.DataFrame,
    feature_names: list[str],
    neg_weight: float = tr.NEG_WEIGHT,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> ModelArtifacts:
    splits = {"train": train_frame, "validation": validation_frame, "test": test_frame}
    clean_splits, matrices, _mean, _std, _pairs = prepare_feature_matrices(splits, feature_names)
    if model_family == "logistic":
        family_artifacts = train_logistic_family(clean_splits, matrices, neg_weight, tr.THRESHOLD_STEPS)
    elif model_family == "regime_dual_logistic":
        family_artifacts = train_regime_dual_logistic_family(clean_splits, matrices, neg_weight, tr.THRESHOLD_STEPS, gate_feature)
    else:
        raise ValueError(f"Unsupported model family: {model_family}")

    return {
        "model_family": model_family,
        "clean_splits": clean_splits,
        "matrices": matrices,
        "weights": cast(np.ndarray, family_artifacts.get("weights")) if family_artifacts.get("weights") is not None else None,
        "negative_weights": cast(np.ndarray, family_artifacts.get("negative_weights")) if family_artifacts.get("negative_weights") is not None else None,
        "positive_weights": cast(np.ndarray, family_artifacts.get("positive_weights")) if family_artifacts.get("positive_weights") is not None else None,
        "threshold": float(cast(float, family_artifacts["threshold"])),
        "validation_y": cast(np.ndarray, family_artifacts["validation_y"]),
        "test_y": cast(np.ndarray, family_artifacts["test_y"]),
        "validation_probabilities": cast(np.ndarray, family_artifacts["validation_probabilities"]),
        "test_probabilities": cast(np.ndarray, family_artifacts["test_probabilities"]),
        "gate_feature": cast(str, family_artifacts.get("gate_feature")) if family_artifacts.get("gate_feature") is not None else None,
    }


def evaluate_seeds(
    frame: pd.DataFrame,
    extra_features: tuple[str, ...],
    neg_weight: float = tr.NEG_WEIGHT,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> list[ModelResult]:
    feature_names = get_feature_names(extra_features)
    results: list[ModelResult] = []
    for seed in (1, 2, 3):
        np.random.seed(seed)
        result, _ = train_model(
            frame,
            f"seed_{seed}",
            extra_features=extra_features,
            neg_weight=neg_weight,
            model_family=model_family,
            gate_feature=gate_feature,
        )
        result.name = f"seed_{seed}"
        result.feature_names = feature_names
        results.append(result)
    return results


def evaluate_walk_forward(
    frame: pd.DataFrame,
    extra_features: tuple[str, ...],
    neg_weight: float = tr.NEG_WEIGHT,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> list[ForwardFoldResult]:
    feature_names = get_feature_names(extra_features)
    rows: list[ForwardFoldResult] = []
    for fold_idx, (train_frame, validation_frame, test_frame) in enumerate(walk_forward_splits(frame), start=1):
        result = fit_on_custom_splits(
            train_frame,
            validation_frame,
            test_frame,
            feature_names,
            neg_weight=neg_weight,
            model_family=model_family,
            gate_feature=gate_feature,
        )
        result.fold_name = f"fold_{fold_idx}"
        rows.append(result)
    return rows


def evaluate_walk_forward_with_folds(
    frame: pd.DataFrame,
    extra_features: tuple[str, ...],
    folds: int,
    neg_weight: float = tr.NEG_WEIGHT,
    model_family: str = "logistic",
    gate_feature: str = "above_200dma_flag",
) -> list[ForwardFoldResult]:
    feature_names = get_feature_names(extra_features)
    rows: list[ForwardFoldResult] = []
    for fold_idx, (train_frame, validation_frame, test_frame) in enumerate(walk_forward_splits(frame, folds=folds), start=1):
        result = fit_on_custom_splits(
            train_frame,
            validation_frame,
            test_frame,
            feature_names,
            neg_weight=neg_weight,
            model_family=model_family,
            gate_feature=gate_feature,
        )
        result.fold_name = f"fold_{fold_idx}"
        rows.append(result)
    return rows


def forward_trade_summary(
    frame: pd.DataFrame,
    extra_features: tuple[str, ...],
    rule: str,
    folds: int = 4,
    neg_weight: float = tr.NEG_WEIGHT,
) -> dict[str, float]:
    feature_names = get_feature_names(extra_features)
    trade_returns: list[float] = []
    trade_hits: list[float] = []
    trade_count = 0
    for train_frame, validation_frame, test_frame in walk_forward_splits(frame, folds=folds):
        artifacts = train_custom_model(train_frame, validation_frame, test_frame, feature_names, neg_weight=neg_weight)
        clean_splits = artifacts["clean_splits"]
        matrices = artifacts["matrices"]
        test_probs = tr.sigmoid(matrices["test"] @ artifacts["weights"])
        future_returns = clean_splits["test"][FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
        selected, cutoff = classify_probs_by_rule(test_probs, float(artifacts["threshold"]), rule)
        backtest = run_non_overlap_backtest(
            clean_splits["test"]["date"], future_returns, selected.astype(bool), pr.HORIZON_DAYS, float(cutoff)
        )
        trade_count += backtest.selected_count
        if backtest.selected_count:
            chosen = []
            idx = 0
            while idx < len(selected):
                if selected[idx]:
                    chosen.append(float(future_returns[idx]))
                    idx += pr.HORIZON_DAYS
                else:
                    idx += 1
            trade_returns.extend(chosen)
            trade_hits.extend([1.0 if x > 0 else 0.0 for x in chosen])
    returns = np.asarray(trade_returns, dtype=np.float64)
    return {
        "trade_count": trade_count,
        "hit_rate": float(np.mean(trade_hits)) if trade_hits else 0.0,
        "avg_return": float(returns.mean()) if len(returns) else 0.0,
    }


def signal_bucket_summary(model_name: str, artifacts: dict[str, object]) -> list[dict[str, object]]:
    test_frame = artifacts["clean_splits"]["test"]
    probs = np.asarray(artifacts["test_probabilities"], dtype=np.float64)
    threshold = float(artifacts["threshold"])
    future_returns = test_frame[FUTURE_RETURN_COLUMN].to_numpy(dtype=np.float64)
    history_probs = np.concatenate(
        [np.asarray(artifacts["validation_probabilities"], dtype=np.float64), np.asarray(artifacts["test_probabilities"], dtype=np.float64)]
    )
    rows: list[dict[str, object]] = []
    signal_names = ["weak_bullish", "bullish", "strong_bullish", "very_strong_bullish"]
    signals = [live.classify_signal(float(prob), threshold, history_probs)[0] for prob in probs]
    for signal_name in signal_names:
        mask = np.asarray([signal == signal_name for signal in signals], dtype=bool)
        bucket_returns = future_returns[mask]
        rows.append(
            {
                "model_name": model_name,
                "signal_name": signal_name,
                "sample_count": int(mask.sum()),
                "hit_rate": float((bucket_returns > 0).mean()) if len(bucket_returns) else 0.0,
                "avg_return": float(bucket_returns.mean()) if len(bucket_returns) else 0.0,
            }
        )
    return rows


def compare_model_signal_buckets(model_rows: list[tuple[str, dict[str, object]]]) -> pd.DataFrame:
    frames = [pd.DataFrame(signal_bucket_summary(model_name, artifacts)) for model_name, artifacts in model_rows]
    return pd.concat(frames, ignore_index=True)


def score_frame(
    frame: pd.DataFrame, feature_names: list[str], mean: np.ndarray, std: np.ndarray, pair_indices: tuple[tuple[int, int], ...], weights: np.ndarray
) -> np.ndarray:
    matrix = frame[feature_names].to_numpy(dtype=np.float32)
    standardized = (matrix - mean) / std
    standardized = add_interactions(standardized, pair_indices)
    standardized = tr.add_bias(standardized)
    return tr.sigmoid(standardized @ weights)


def regime_summary(frame: pd.DataFrame) -> pd.DataFrame:
    summary_frames: list[pd.DataFrame] = []
    splits = split_frame(frame)
    for split_name in ("validation", "test"):
        split_frame_df = splits[split_name].copy()
        split_frame_df["year_bucket"] = split_frame_df["date"].dt.year.astype(int)
        grouped = (
            split_frame_df.groupby("year_bucket", as_index=False)
            .agg(
                rows=(pr.TARGET_COLUMN, "size"),
                positive_rate=(pr.TARGET_COLUMN, "mean"),
                avg_future_return=(FUTURE_RETURN_COLUMN, "mean"),
            )
            .assign(split=split_name)
        )
        summary_frames.append(grouped[["split", "year_bucket", "rows", "positive_rate", "avg_future_return"]])
    return pd.concat(summary_frames, ignore_index=True)


def stage_positive_rate_summary(full_frame: pd.DataFrame, models: dict[str, ModelArtifacts]) -> pd.DataFrame:
    periods = [
        ("2008_2010", "2008-01-01", "2010-12-31"),
        ("2011_2019", "2011-01-01", "2019-12-31"),
        ("2020_2023", "2020-01-01", "2023-12-31"),
        ("2024_plus", "2024-01-01", None),
    ]
    rows: list[dict[str, object]] = []
    for model_name, artifacts in models.items():
        clean_splits = cast(dict[str, pd.DataFrame], artifacts["clean_splits"])
        clean_frame = pd.concat(
            [
                clean_splits["train"],
                clean_splits["validation"],
                clean_splits["test"],
            ],
            ignore_index=True,
        )
        probs = score_frame(
            clean_frame,
            cast(list[str], artifacts["feature_names"]),
            cast(np.ndarray, artifacts["train_mean"]),
            cast(np.ndarray, artifacts["train_std"]),
            cast(tuple[tuple[int, int], ...], artifacts["pair_indices"]),
            cast(np.ndarray, artifacts["weights"]),
        )
        clean_frame = clean_frame.assign(predicted_positive=(probs >= float(artifacts["threshold"])).astype(float))
        for label, start, end in periods:
            mask = clean_frame["date"] >= pd.Timestamp(start)
            if end is not None:
                mask &= clean_frame["date"] <= pd.Timestamp(end)
            bucket = clean_frame.loc[mask]
            rows.append(
                {
                    "model_name": model_name,
                    "period": label,
                    "rows": len(bucket),
                    "predicted_positive_rate": float(bucket["predicted_positive"].mean()) if len(bucket) else 0.0,
                }
            )
    return pd.DataFrame(rows)


def round_float(value: float) -> float:
    return round(float(value), 4)


def main() -> None:
    ensure_cache_dir()
    raw = pr.download_asset_prices()
    default_frame = build_labeled_frame(raw)

    model_specs = [
        ("ret_60", ("ret_60",), ()),
        ("sma_gap_60", ("sma_gap_60",), ()),
        ("ret_60_plus_sma_gap_60", ("ret_60", "sma_gap_60"), ()),
        ("ret_60_plus_sma_gap_60_plus_default_interaction", ("ret_60", "sma_gap_60"), ()),
        ("ret_60_replaces_ret_20", ("ret_60",), ("ret_20",)),
        ("ret_60_plus_year", ("ret_60", "year"), ()),
        ("ret_60_plus_rolling_return_120", ("ret_60", "rolling_return_120"), ()),
        ("ret_60_plus_rolling_vol_60", ("ret_60", "rolling_vol_60"), ()),
        ("ret_60_plus_all_regime_features", ("ret_60", "year", "rolling_return_120", "rolling_vol_60"), ()),
        ("ret_60_plus_sma_gap_60_plus_neg_weight_1_1", ("ret_60", "sma_gap_60"), ()),
        ("ret_60_plus_sma_gap_60_plus_neg_weight_1_15", ("ret_60", "sma_gap_60"), ()),
        ("ret_60_plus_sma_gap_60_plus_rolling_vol_60", ("ret_60", "sma_gap_60", "rolling_vol_60"), ()),
        ("ret_120", ("ret_120",), ()),
        ("sma_gap_120", ("sma_gap_120",), ()),
        ("drawdown_120", ("drawdown_120",), ()),
        ("volume_vs_120", ("volume_vs_120",), ()),
        ("sma_gap_60_plus_sma_gap_120", ("sma_gap_60", "sma_gap_120"), ()),
        ("sma_gap_60_plus_sma_gap_120_plus_neg_weight_1_15", ("sma_gap_60", "sma_gap_120"), ()),
        ("distance_to_252_high", ("distance_to_252_high",), ()),
        ("close_location_20", ("close_location_20",), ()),
        ("up_day_ratio_20", ("up_day_ratio_20",), ()),
        ("above_200dma_flag", ("above_200dma_flag",), ()),
        ("atr_pct_20", ("atr_pct_20",), ()),
        ("ret_60_plus_sma_gap_60_plus_distance_to_252_high", ("ret_60", "sma_gap_60", "distance_to_252_high"), ()),
        ("ret_60_plus_sma_gap_60_plus_close_location_20", ("ret_60", "sma_gap_60", "close_location_20"), ()),
        ("ret_60_plus_sma_gap_60_plus_up_day_ratio_20", ("ret_60", "sma_gap_60", "up_day_ratio_20"), ()),
        ("ret_60_plus_sma_gap_60_plus_above_200dma_flag", ("ret_60", "sma_gap_60", "above_200dma_flag"), ()),
        ("ret_60_plus_sma_gap_60_plus_atr_pct_20", ("ret_60", "sma_gap_60", "atr_pct_20"), ()),
        ("ret_60_plus_sma_gap_60_interaction", ("ret_60", "sma_gap_60"), ()),
    ]

    model_results: dict[str, ModelResult] = {}
    model_artifacts: dict[str, dict[str, object]] = {}
    for name, extras, drops in model_specs:
        neg_weight = None
        if name == "ret_60_plus_sma_gap_60_plus_neg_weight_1_1":
            neg_weight = 1.1
        if name == "ret_60_plus_sma_gap_60_plus_neg_weight_1_15":
            neg_weight = 1.15
        if name == "sma_gap_60_plus_sma_gap_120_plus_neg_weight_1_15":
            neg_weight = 1.15
        extra_interactions = (("ret_60", "sma_gap_60"),) if name == "ret_60_plus_sma_gap_60_interaction" else ()
        result, artifacts = train_model(
            default_frame,
            name,
            extra_features=extras,
            drop_features=drops,
            extra_interactions=extra_interactions,
            neg_weight=neg_weight,
        )
        model_results[name] = result
        model_artifacts[name] = artifacts
        model_artifacts[name]["feature_names"] = result.feature_names

    backtests: list[BacktestResult] = []
    for model_name in ("ret_60", "sma_gap_60", "ret_60_plus_sma_gap_60", "ret_60_plus_sma_gap_60_plus_neg_weight_1_15"):
        backtests.extend(backtest_rules(model_name, model_artifacts[model_name]))
    backtests.extend(
        fixed_threshold_backtests("ret_60_plus_sma_gap_60", model_artifacts["ret_60_plus_sma_gap_60"], (0.47, 0.49, 0.51))
    )
    backtests.extend(cooldown_backtests("ret_60_plus_sma_gap_60", model_artifacts["ret_60_plus_sma_gap_60"], (5, 10)))
    backtests.extend(
        fixed_threshold_backtests(
            "ret_60_plus_sma_gap_60_plus_neg_weight_1_15",
            model_artifacts["ret_60_plus_sma_gap_60_plus_neg_weight_1_15"],
            (0.47, 0.49, 0.51),
        )
    )

    backtest_frame = pd.DataFrame(
        [
            {
                "model_name": row.model_name,
                "rule_name": row.rule_name,
                "selected_count": row.selected_count,
                "hit_rate": round_float(row.hit_rate),
                "avg_return": round_float(row.avg_return),
                "max_drawdown_simple": round_float(row.max_drawdown_simple),
                "max_drawdown_compound": round_float(row.max_drawdown_compound),
                "longest_win_streak": row.longest_win_streak,
                "longest_loss_streak": row.longest_loss_streak,
                "threshold_or_cutoff": round_float(row.threshold_or_cutoff),
            }
            for row in backtests
        ]
    )
    backtest_frame.to_csv(BACKTEST_OUTPUT_PATH, sep="\t", index=False)

    regime_frame = regime_summary(default_frame)
    stage_frame = stage_positive_rate_summary(
        default_frame,
        {"ret_60": model_artifacts["ret_60"], "sma_gap_60": model_artifacts["sma_gap_60"]},
    )
    combined_regime = pd.concat(
        [
            regime_frame.assign(summary_type="yearly_barrier"),
            stage_frame.assign(summary_type="stage_model_positive_rate"),
        ],
        ignore_index=True,
        sort=False,
    )
    combined_regime.to_csv(REGIME_OUTPUT_PATH, sep="\t", index=False)

    label_configs = [
        ("80d_8_4_ret_60", 80, 0.08, -0.04),
        ("120d_8_4_ret_60", 120, 0.08, -0.04),
        ("60d_12_6_ret_60", 60, 0.12, -0.06),
    ]
    label_results: dict[str, ModelResult] = {}
    for name, horizon, upper, lower in label_configs:
        frame = build_labeled_frame(raw, horizon_days=horizon, upper_barrier=upper, lower_barrier=lower)
        result, _ = train_model(frame, name, extra_features=("ret_60",))
        label_results[name] = result

    combo_seed_results = evaluate_seeds(default_frame, ("ret_60", "sma_gap_60"))
    combo_walk_forward = evaluate_walk_forward(default_frame, ("ret_60", "sma_gap_60"))
    combo_walk_forward_4fold = evaluate_walk_forward_with_folds(default_frame, ("ret_60", "sma_gap_60"), folds=4)
    combo_neg115_seed_results = evaluate_seeds(default_frame, ("ret_60", "sma_gap_60"), neg_weight=1.15)
    combo_neg115_walk_forward_4fold = evaluate_walk_forward_with_folds(default_frame, ("ret_60", "sma_gap_60"), folds=4, neg_weight=1.15)
    ret60_walk_forward = evaluate_walk_forward(default_frame, ("ret_60",))
    combo_trade_forward_threshold = forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "threshold", folds=4)
    combo_neg115_trade_forward_threshold = forward_trade_summary(
        default_frame, ("ret_60", "sma_gap_60"), "threshold", folds=4, neg_weight=1.15
    )
    sma_gap_trade_forward_top15 = forward_trade_summary(default_frame, ("sma_gap_60",), "top_15pct", folds=4)
    rule_comparison = pd.DataFrame(
        rule_comparison_rows(
            "ret_60_plus_sma_gap_60",
            model_artifacts["ret_60_plus_sma_gap_60"],
            ("threshold", "fixed_0.47", "fixed_0.49", "top_12_5pct", "top_15pct", "top_17_5pct", "top_20pct"),
        )
        + rule_comparison_rows(
            "ret_60_plus_sma_gap_60_plus_neg_weight_1_15",
            model_artifacts["ret_60_plus_sma_gap_60_plus_neg_weight_1_15"],
            ("threshold", "fixed_0.47", "fixed_0.49", "top_15pct", "top_17_5pct", "top_20pct"),
        )
    )
    forward_rule_summary = pd.DataFrame(
        [
            {
                "strategy_name": "combo_threshold",
                "rule_name": "threshold",
                **combo_trade_forward_threshold,
            },
            {
                "strategy_name": "combo_fixed_0_49",
                "rule_name": "fixed_0.49",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "fixed_0.49", folds=4),
            },
            {
                "strategy_name": "combo_top_12_5pct",
                "rule_name": "top_12_5pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_12_5pct", folds=4),
            },
            {
                "strategy_name": "combo_top_15pct",
                "rule_name": "top_15pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_15pct", folds=4),
            },
            {
                "strategy_name": "combo_top_17_5pct",
                "rule_name": "top_17_5pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_17_5pct", folds=4),
            },
            {
                "strategy_name": "combo_top_20pct",
                "rule_name": "top_20pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_20pct", folds=4),
            },
            {
                "strategy_name": "combo_neg115_top_17_5pct",
                "rule_name": "top_17_5pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_17_5pct", folds=4, neg_weight=1.15),
            },
            {
                "strategy_name": "combo_neg115_threshold",
                "rule_name": "threshold",
                **combo_neg115_trade_forward_threshold,
            },
            {
                "strategy_name": "combo_neg115_fixed_0_47",
                "rule_name": "fixed_0.47",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "fixed_0.47", folds=4, neg_weight=1.15),
            },
            {
                "strategy_name": "combo_neg115_fixed_0_49",
                "rule_name": "fixed_0.49",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "fixed_0.49", folds=4, neg_weight=1.15),
            },
            {
                "strategy_name": "combo_neg115_top_15pct",
                "rule_name": "top_15pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_15pct", folds=4, neg_weight=1.15),
            },
            {
                "strategy_name": "combo_neg115_top_20pct",
                "rule_name": "top_20pct",
                **forward_trade_summary(default_frame, ("ret_60", "sma_gap_60"), "top_20pct", folds=4, neg_weight=1.15),
            },
            {"strategy_name": "sma_gap_60_top15", "rule_name": "top_15pct", **sma_gap_trade_forward_top15},
        ]
    )

    combo_artifacts = model_artifacts["ret_60_plus_sma_gap_60"]
    precision_summary = {
        "validation": precision_recall(
            np.asarray(combo_artifacts["validation_probabilities"], dtype=np.float64),
            combo_artifacts["clean_splits"]["validation"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32),
            float(combo_artifacts["threshold"]),
        ),
        "test": precision_recall(
            np.asarray(combo_artifacts["test_probabilities"], dtype=np.float64),
            combo_artifacts["clean_splits"]["test"][pr.TARGET_COLUMN].to_numpy(dtype=np.float32),
            float(combo_artifacts["threshold"]),
        ),
    }

    threshold_scan_results: dict[str, ModelResult] = {}
    for steps in (401, 801, 1201):
        result, _ = train_model(
            default_frame,
            f"ret_60_plus_sma_gap_60_threshold_steps_{steps}",
            extra_features=("ret_60", "sma_gap_60"),
            threshold_steps=steps,
        )
        threshold_scan_results[str(steps)] = result

    combo_neg_weight_scan: dict[str, ModelResult] = {}
    for neg_weight in (1.05, 1.15):
        result, _ = train_model(
            default_frame,
            f"ret_60_plus_sma_gap_60_neg_weight_{neg_weight:.2f}",
            extra_features=("ret_60", "sma_gap_60"),
            neg_weight=neg_weight,
        )
        combo_neg_weight_scan[f"{neg_weight:.2f}"] = result

    combo_signal_summary = signal_bucket_summary("ret_60_plus_sma_gap_60", model_artifacts["ret_60_plus_sma_gap_60"])
    combo_neg115_signal_summary = signal_bucket_summary(
        "ret_60_plus_sma_gap_60_plus_neg_weight_1_15",
        model_artifacts["ret_60_plus_sma_gap_60_plus_neg_weight_1_15"],
    )
    compare_model_signal_buckets(
        [
            ("ret_60_plus_sma_gap_60", model_artifacts["ret_60_plus_sma_gap_60"]),
            ("ret_60_plus_sma_gap_60_plus_neg_weight_1_15", model_artifacts["ret_60_plus_sma_gap_60_plus_neg_weight_1_15"]),
        ]
    ).to_csv(SIGNAL_OUTPUT_PATH, sep="\t", index=False)
    rule_comparison.to_csv(RULE_OUTPUT_PATH, sep="\t", index=False)
    forward_rule_summary.to_csv(FORWARD_OUTPUT_PATH, sep="\t", index=False)

    round_payload = {
        "models": {name: asdict(result) for name, result in model_results.items()},
        "backtests": [asdict(row) for row in backtests],
        "label_sweeps": {name: asdict(result) for name, result in label_results.items()},
        "combo_seed_results": [asdict(row) for row in combo_seed_results],
        "combo_walk_forward": [asdict(row) for row in combo_walk_forward],
        "combo_walk_forward_4fold": [asdict(row) for row in combo_walk_forward_4fold],
        "combo_neg115_seed_results": [asdict(row) for row in combo_neg115_seed_results],
        "combo_neg115_walk_forward_4fold": [asdict(row) for row in combo_neg115_walk_forward_4fold],
        "ret60_walk_forward": [asdict(row) for row in ret60_walk_forward],
        "combo_precision_summary": precision_summary,
        "combo_threshold_scan": {name: asdict(result) for name, result in threshold_scan_results.items()},
        "combo_neg_weight_scan": {name: asdict(result) for name, result in combo_neg_weight_scan.items()},
        "combo_trade_forward_threshold": combo_trade_forward_threshold,
        "combo_neg115_trade_forward_threshold": combo_neg115_trade_forward_threshold,
        "sma_gap_trade_forward_top15": sma_gap_trade_forward_top15,
        "rule_comparison": rule_comparison.to_dict(orient="records"),
        "forward_rule_summary": forward_rule_summary.to_dict(orient="records"),
        "combo_signal_summary": combo_signal_summary,
        "combo_neg115_signal_summary": combo_neg115_signal_summary,
    }
    with open(ROUND_OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(round_payload, f, indent=2)
    print(json.dumps(round_payload, indent=2))


if __name__ == "__main__":
    main()
