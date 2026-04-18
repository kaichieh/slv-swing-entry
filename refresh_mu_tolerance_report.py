from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

import asset_config as ac
import prepare
import train

ASSET_KEY = "mu"
LIVE_LABEL_MODE = "future-return-top-bottom-30pct"
CHALLENGER_LABEL_MODE = "future-return-top-bottom-20pct"
TOP_PCT = 11.5
TOLERANCE_VARIANTS = (0.0, 0.001, 0.0025, 0.005)
FOLDS = 3
POCKET_LABEL = "above_200dma_and_slope60_positive"
FEATURE_NAMES = list(train.FEATURE_COLUMNS) + ["ret_60", "vol_ratio_20_120"]
TARGET_COLUMN = prepare.TARGET_COLUMN
POCKET_COLUMNS = ["above_200dma_flag", "slope_60"]


@dataclass
class ModelArtifacts:
    feature_names: list[str]
    mean: np.ndarray
    std: np.ndarray
    active_pairs: list[tuple[int, int]]
    weights: np.ndarray
    threshold: float
    validation_probabilities: np.ndarray


def get_output_dir() -> Path:
    return ac.get_asset_dir(ASSET_KEY)


def get_summary_path() -> Path:
    return get_output_dir() / "tolerance_variant_compare.tsv"


def get_fold_path() -> Path:
    return get_output_dir() / "tolerance_fold_compare.tsv"


def get_recovery_path() -> Path:
    return get_output_dir() / "tolerance_recovered_cases.tsv"


def with_env(name: str, value: str):
    class _EnvContext:
        def __enter__(self):
            self.previous = os.environ.get(name)
            os.environ[name] = value

        def __exit__(self, exc_type, exc, tb):
            if self.previous is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = self.previous

    return _EnvContext()


def build_label_frame(raw_prices: pd.DataFrame, label_mode: str) -> pd.DataFrame:
    with with_env("AR_LABEL_MODE", label_mode):
        frame = prepare.add_features(raw_prices.copy())
    return frame.sort_values("date").reset_index(drop=True)


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


def build_shared_axis(tb30_frame: pd.DataFrame, tb20_frame: pd.DataFrame) -> pd.DataFrame:
    shared = (
        tb30_frame[["date", "future_return_60", *POCKET_COLUMNS]]
        .merge(tb20_frame[["date"]], on="date", how="inner")
        .dropna(subset=["future_return_60", *POCKET_COLUMNS])
        .sort_values("date")
        .reset_index(drop=True)
    )
    shared["pocket"] = (shared["above_200dma_flag"] == 1.0) & (shared["slope_60"] > 0.0)
    return shared


def split_by_shared_dates(
    frame: pd.DataFrame,
    train_dates: pd.Series,
    validation_dates: pd.Series,
    test_dates: pd.Series,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train_frame = frame[frame["date"].isin(set(train_dates))].copy().reset_index(drop=True)
    validation_frame = frame[frame["date"].isin(set(validation_dates))].copy().reset_index(drop=True)
    test_frame = frame[frame["date"].isin(set(test_dates))].copy().reset_index(drop=True)
    return train_frame, validation_frame, test_frame


def build_interaction_pairs(feature_names: list[str]) -> list[tuple[int, int]]:
    feature_index = {name: idx for idx, name in enumerate(feature_names)}
    pairs: list[tuple[int, int]] = []
    for left, right in train.DEFAULT_INTERACTION_FEATURE_PAIRS:
        if left in feature_index and right in feature_index:
            pairs.append((feature_index[left], feature_index[right]))
    return pairs


def transform_features(
    frame: pd.DataFrame,
    feature_names: list[str],
    mean: np.ndarray,
    std: np.ndarray,
    active_pairs: list[tuple[int, int]],
) -> np.ndarray:
    matrix = frame[feature_names].to_numpy(dtype=np.float32)
    standardized = (matrix - mean) / std
    if active_pairs:
        extras = [standardized[:, i : i + 1] * standardized[:, j : j + 1] for i, j in active_pairs]
        standardized = np.concatenate([standardized] + extras, axis=1)
    return train.add_bias(standardized)


def fit_model(train_frame: pd.DataFrame, validation_frame: pd.DataFrame) -> ModelArtifacts:
    train.set_seed(train.SEED)
    train_x = train_frame[FEATURE_NAMES].to_numpy(dtype=np.float32)
    validation_x = validation_frame[FEATURE_NAMES].to_numpy(dtype=np.float32)
    train_y = train_frame[TARGET_COLUMN].to_numpy(dtype=np.float32)
    validation_y = validation_frame[TARGET_COLUMN].to_numpy(dtype=np.float32)

    mean = train_x.mean(axis=0, keepdims=True)
    std = train_x.std(axis=0, keepdims=True)
    std = np.where(std < 1e-6, 1.0, std)
    active_pairs = build_interaction_pairs(FEATURE_NAMES)

    transformed_train = transform_features(train_frame, FEATURE_NAMES, mean, std, active_pairs)
    transformed_validation = transform_features(validation_frame, FEATURE_NAMES, mean, std, active_pairs)

    weights = np.zeros(transformed_train.shape[1], dtype=np.float32)
    best_weights = weights.copy()
    best_validation_f1 = -np.inf
    best_threshold = 0.5
    epochs_without_improvement = 0

    for _ in range(train.MAX_EPOCHS):
        logits = transformed_train @ weights
        probs = train.sigmoid(logits)
        gradient = transformed_train.T @ (probs - train_y) / transformed_train.shape[0]
        gradient[:-1] += train.L2_REG * weights[:-1]
        weights -= train.LEARNING_RATE * gradient

        validation_logits = transformed_validation @ weights
        threshold = train.select_threshold(
            train.sigmoid(validation_logits),
            validation_y,
            primary_metric="balanced_accuracy",
        )
        validation_metrics = train.compute_metrics(
            validation_logits,
            validation_y,
            validation_frame["future_return_60"].to_numpy(dtype=np.float32),
            threshold,
        )
        if validation_metrics.f1 > best_validation_f1:
            best_validation_f1 = validation_metrics.f1
            best_weights = weights.copy()
            best_threshold = threshold
            epochs_without_improvement = 0
        else:
            epochs_without_improvement += 1
        if epochs_without_improvement >= train.PATIENCE:
            break

    validation_probabilities = train.sigmoid(transformed_validation @ best_weights)
    return ModelArtifacts(
        feature_names=list(FEATURE_NAMES),
        mean=mean,
        std=std,
        active_pairs=active_pairs,
        weights=best_weights,
        threshold=float(best_threshold),
        validation_probabilities=validation_probabilities,
    )


def score_frame(frame: pd.DataFrame, artifacts: ModelArtifacts) -> np.ndarray:
    matrix = transform_features(frame, artifacts.feature_names, artifacts.mean, artifacts.std, artifacts.active_pairs)
    return train.sigmoid(matrix @ artifacts.weights)


def top_pct_cutoff(validation_probabilities: np.ndarray, top_pct: float = TOP_PCT) -> float:
    return float(np.quantile(validation_probabilities, 1.0 - top_pct / 100.0))


def apply_non_overlap(frame: pd.DataFrame, selected_column: str) -> pd.Series:
    selected = frame[selected_column].to_numpy(dtype=bool)
    keep = np.zeros(len(frame), dtype=bool)
    next_allowed_idx = -1
    for idx, is_selected in enumerate(selected):
        if not is_selected or idx < next_allowed_idx:
            continue
        keep[idx] = True
        next_allowed_idx = idx + int(prepare.HORIZON_DAYS)
    return pd.Series(keep, index=frame.index)


def compute_compound_drawdown(returns: pd.Series) -> float:
    if returns.empty:
        return 0.0
    curve = (1.0 + returns.to_numpy(dtype=float)).cumprod()
    peaks = np.maximum.accumulate(curve)
    drawdown = curve / peaks - 1.0
    return float(drawdown.min())


def compute_strategy_stats(frame: pd.DataFrame, selected_column: str) -> dict[str, float]:
    selected_rows = frame[frame[selected_column]].copy()
    episode_mask = apply_non_overlap(frame, selected_column)
    episode_rows = frame[episode_mask].copy()
    if episode_rows.empty:
        return {
            "selected_rows": float(len(selected_rows)),
            "episode_count": 0.0,
            "episode_hit_rate": 0.0,
            "episode_avg_return": 0.0,
            "episode_max_drawdown_compound": 0.0,
        }
    returns = episode_rows["future_return_60"]
    return {
        "selected_rows": float(len(selected_rows)),
        "episode_count": float(len(episode_rows)),
        "episode_hit_rate": float((returns > 0).mean()),
        "episode_avg_return": float(returns.mean()),
        "episode_max_drawdown_compound": compute_compound_drawdown(returns),
    }


def build_shared_scored_frame(
    shared_test: pd.DataFrame,
    live_test: pd.DataFrame,
    challenger_test: pd.DataFrame,
    live_artifacts: ModelArtifacts,
    challenger_artifacts: ModelArtifacts,
) -> pd.DataFrame:
    live_probs = (
        live_test[["date"]]
        .assign(live_probability=score_frame(live_test, live_artifacts))
        .sort_values("date")
    )
    challenger_probs = (
        challenger_test[["date"]]
        .assign(shadow_probability=score_frame(challenger_test, challenger_artifacts))
        .sort_values("date")
    )
    frame = (
        shared_test.merge(live_probs, on="date", how="inner")
        .merge(challenger_probs, on="date", how="inner")
        .sort_values("date")
        .reset_index(drop=True)
    )
    frame["live_cutoff"] = top_pct_cutoff(live_artifacts.validation_probabilities)
    frame["shadow_cutoff"] = top_pct_cutoff(challenger_artifacts.validation_probabilities)
    frame["live_selected"] = frame["live_probability"] >= frame["live_cutoff"]
    frame["shadow_selected_base"] = frame["shadow_probability"] >= frame["shadow_cutoff"]
    frame["shadow_gap"] = frame["shadow_probability"] - frame["shadow_cutoff"]
    frame["live_gap"] = frame["live_probability"] - frame["live_cutoff"]
    return frame


def summarize_variant(
    name: str,
    full_oos_frame: pd.DataFrame,
    fold_frames: list[pd.DataFrame],
    tolerance: float,
) -> dict[str, object]:
    variant_column = f"shadow_selected_{name}"
    full_oos_stats = compute_strategy_stats(full_oos_frame, variant_column)
    full_oos_live_stats = compute_strategy_stats(full_oos_frame, "live_selected")
    recovered_mask = (
        full_oos_frame["live_selected"]
        & (~full_oos_frame["shadow_selected_base"])
        & full_oos_frame["pocket"]
        & full_oos_frame[variant_column]
    )
    live_only_pocket_mask = (
        full_oos_frame["live_selected"] & (~full_oos_frame["shadow_selected_base"]) & full_oos_frame["pocket"]
    )
    recovered_rows = full_oos_frame[recovered_mask].copy()

    fold_stats = [compute_strategy_stats(frame, variant_column) for frame in fold_frames]
    live_fold_stats = [compute_strategy_stats(frame, "live_selected") for frame in fold_frames]
    pooled_fold_episodes = float(sum(item["episode_count"] for item in fold_stats))
    mean_fold_hit_rate = float(np.mean([item["episode_hit_rate"] for item in fold_stats])) if fold_stats else 0.0
    mean_fold_avg_return = float(np.mean([item["episode_avg_return"] for item in fold_stats])) if fold_stats else 0.0
    min_fold_avg_return = float(np.min([item["episode_avg_return"] for item in fold_stats])) if fold_stats else 0.0
    worst_fold_drawdown = float(np.min([item["episode_max_drawdown_compound"] for item in fold_stats])) if fold_stats else 0.0
    mean_fold_vs_live_return = (
        float(np.mean([item["episode_avg_return"] - live["episode_avg_return"] for item, live in zip(fold_stats, live_fold_stats)]))
        if fold_stats
        else 0.0
    )

    return {
        "variant": name,
        "monitoring_scope": "side_probe_only",
        "tolerance": tolerance,
        "pocket_label": POCKET_LABEL,
        "full_oos_selected_rows": int(full_oos_stats["selected_rows"]),
        "full_oos_episode_count": int(full_oos_stats["episode_count"]),
        "full_oos_episode_hit_rate": round(float(full_oos_stats["episode_hit_rate"]), 4),
        "full_oos_episode_avg_return": round(float(full_oos_stats["episode_avg_return"]), 4),
        "full_oos_episode_max_drawdown_compound": round(float(full_oos_stats["episode_max_drawdown_compound"]), 4),
        "live_full_oos_episode_count": int(full_oos_live_stats["episode_count"]),
        "live_full_oos_episode_hit_rate": round(float(full_oos_live_stats["episode_hit_rate"]), 4),
        "live_full_oos_episode_avg_return": round(float(full_oos_live_stats["episode_avg_return"]), 4),
        "live_full_oos_episode_max_drawdown_compound": round(float(full_oos_live_stats["episode_max_drawdown_compound"]), 4),
        "full_oos_episode_avg_return_vs_live": round(
            float(full_oos_stats["episode_avg_return"] - full_oos_live_stats["episode_avg_return"]),
            4,
        ),
        "full_oos_episode_hit_rate_vs_live": round(
            float(full_oos_stats["episode_hit_rate"] - full_oos_live_stats["episode_hit_rate"]),
            4,
        ),
        "full_oos_live_only_pocket_cases": int(live_only_pocket_mask.sum()),
        "full_oos_recovered_cases": int(recovered_mask.sum()),
        "full_oos_recovery_share": round(float(recovered_mask.sum() / max(live_only_pocket_mask.sum(), 1)), 4),
        "full_oos_recovered_avg_return": round(float(recovered_rows["future_return_60"].mean()) if len(recovered_rows) else 0.0, 4),
        "full_oos_recovered_hit_rate": round(float((recovered_rows["future_return_60"] > 0).mean()) if len(recovered_rows) else 0.0, 4),
        "full_oos_recovered_shadow_gap_median": round(float(recovered_rows["shadow_gap"].median()) if len(recovered_rows) else 0.0, 6),
        "pooled_fold_episodes": int(pooled_fold_episodes),
        "mean_fold_hit_rate": round(mean_fold_hit_rate, 4),
        "mean_fold_avg_return": round(mean_fold_avg_return, 4),
        "min_fold_avg_return": round(min_fold_avg_return, 4),
        "worst_fold_drawdown_compound": round(worst_fold_drawdown, 4),
        "mean_fold_avg_return_vs_live": round(mean_fold_vs_live_return, 4),
    }


def main() -> None:
    get_output_dir().mkdir(parents=True, exist_ok=True)

    with with_env("AR_ASSET", ASSET_KEY):
        raw_prices = prepare.download_asset_prices()
        tb30_frame = build_label_frame(raw_prices, LIVE_LABEL_MODE)
        tb20_frame = build_label_frame(raw_prices, CHALLENGER_LABEL_MODE)

    shared_axis = build_shared_axis(tb30_frame, tb20_frame)
    split_rows = walk_forward_splits(shared_axis, FOLDS)
    if not split_rows:
        raise RuntimeError("Not enough shared rows to build tolerance walk-forward splits.")

    train_end30, valid_end30 = prepare.split_indices(len(tb30_frame))
    train_end20, valid_end20 = prepare.split_indices(len(tb20_frame))
    full_oos_live_train = tb30_frame.iloc[:train_end30].copy().reset_index(drop=True)
    full_oos_live_validation = tb30_frame.iloc[train_end30:valid_end30].copy().reset_index(drop=True)
    full_oos_live_test = tb30_frame.iloc[valid_end30:].copy().reset_index(drop=True)
    full_oos_shadow_train = tb20_frame.iloc[:train_end20].copy().reset_index(drop=True)
    full_oos_shadow_validation = tb20_frame.iloc[train_end20:valid_end20].copy().reset_index(drop=True)
    full_oos_shadow_test = tb20_frame.iloc[valid_end20:].copy().reset_index(drop=True)
    full_oos_shared_test = (
        full_oos_live_test[["date", "future_return_60", *POCKET_COLUMNS]]
        .merge(full_oos_shadow_test[["date"]], on="date", how="inner")
        .dropna(subset=["future_return_60", *POCKET_COLUMNS])
        .sort_values("date")
        .reset_index(drop=True)
    )
    full_oos_shared_test["pocket"] = (
        (full_oos_shared_test["above_200dma_flag"] == 1.0) & (full_oos_shared_test["slope_60"] > 0.0)
    )
    full_oos_live_artifacts = fit_model(full_oos_live_train, full_oos_live_validation)
    full_oos_shadow_artifacts = fit_model(full_oos_shadow_train, full_oos_shadow_validation)
    full_oos_frame = build_shared_scored_frame(
        full_oos_shared_test,
        full_oos_live_test[full_oos_live_test["date"].isin(set(full_oos_shared_test["date"]))].copy(),
        full_oos_shadow_test[full_oos_shadow_test["date"].isin(set(full_oos_shared_test["date"]))].copy(),
        full_oos_live_artifacts,
        full_oos_shadow_artifacts,
    )

    heldout_name, heldout_train_axis, heldout_validation_axis, heldout_test_axis = split_rows[-1]
    heldout_live_train, heldout_live_validation, heldout_live_test = split_by_shared_dates(
        tb30_frame,
        heldout_train_axis["date"],
        heldout_validation_axis["date"],
        heldout_test_axis["date"],
    )
    heldout_shadow_train, heldout_shadow_validation, heldout_shadow_test = split_by_shared_dates(
        tb20_frame,
        heldout_train_axis["date"],
        heldout_validation_axis["date"],
        heldout_test_axis["date"],
    )
    heldout_live_artifacts = fit_model(heldout_live_train, heldout_live_validation)
    heldout_shadow_artifacts = fit_model(heldout_shadow_train, heldout_shadow_validation)
    heldout_frame = build_shared_scored_frame(
        heldout_test_axis,
        heldout_live_test,
        heldout_shadow_test,
        heldout_live_artifacts,
        heldout_shadow_artifacts,
    )

    fold_frames: list[pd.DataFrame] = []
    fold_rows: list[dict[str, object]] = []
    for fold_name, train_axis, validation_axis, test_axis in split_rows:
        live_train, live_validation, live_test = split_by_shared_dates(
            tb30_frame,
            train_axis["date"],
            validation_axis["date"],
            test_axis["date"],
        )
        shadow_train, shadow_validation, shadow_test = split_by_shared_dates(
            tb20_frame,
            train_axis["date"],
            validation_axis["date"],
            test_axis["date"],
        )
        live_artifacts = fit_model(live_train, live_validation)
        shadow_artifacts = fit_model(shadow_train, shadow_validation)
        fold_frame = build_shared_scored_frame(
            test_axis,
            live_test,
            shadow_test,
            live_artifacts,
            shadow_artifacts,
        )
        fold_frames.append(fold_frame)
        base_live_stats = compute_strategy_stats(fold_frame, "live_selected")
        base_shadow_stats = compute_strategy_stats(fold_frame, "shadow_selected_base")
        fold_rows.append(
            {
                "variant": "live",
                "monitoring_scope": "reference_only",
                "tolerance": "",
                "fold": fold_name,
                "test_start": test_axis["date"].iloc[0].strftime("%Y-%m-%d"),
                "test_end": test_axis["date"].iloc[-1].strftime("%Y-%m-%d"),
                "selected_rows": int(base_live_stats["selected_rows"]),
                "episode_count": int(base_live_stats["episode_count"]),
                "episode_hit_rate": round(float(base_live_stats["episode_hit_rate"]), 4),
                "episode_avg_return": round(float(base_live_stats["episode_avg_return"]), 4),
                "episode_max_drawdown_compound": round(float(base_live_stats["episode_max_drawdown_compound"]), 4),
            }
        )
        fold_rows.append(
            {
                "variant": "shadow_base",
                "monitoring_scope": "challenger_reference",
                "tolerance": 0.0,
                "fold": fold_name,
                "test_start": test_axis["date"].iloc[0].strftime("%Y-%m-%d"),
                "test_end": test_axis["date"].iloc[-1].strftime("%Y-%m-%d"),
                "selected_rows": int(base_shadow_stats["selected_rows"]),
                "episode_count": int(base_shadow_stats["episode_count"]),
                "episode_hit_rate": round(float(base_shadow_stats["episode_hit_rate"]), 4),
                "episode_avg_return": round(float(base_shadow_stats["episode_avg_return"]), 4),
                "episode_max_drawdown_compound": round(float(base_shadow_stats["episode_max_drawdown_compound"]), 4),
            }
        )

    recovery_rows: list[dict[str, object]] = []
    for tolerance in TOLERANCE_VARIANTS:
        variant_name = "shadow_base" if tolerance == 0.0 else f"shadow_tol_{str(tolerance).replace('.', '_')}"
        variant_column = f"shadow_selected_{variant_name}"

        heldout_frame[variant_column] = heldout_frame["shadow_selected_base"] | (
            heldout_frame["pocket"] & (heldout_frame["shadow_probability"] >= (heldout_frame["shadow_cutoff"] - tolerance))
        )
        for fold_frame, fold_tuple in zip(fold_frames, split_rows):
            fold_name = fold_tuple[0]
            fold_frame[variant_column] = fold_frame["shadow_selected_base"] | (
                fold_frame["pocket"] & (fold_frame["shadow_probability"] >= (fold_frame["shadow_cutoff"] - tolerance))
            )
            if tolerance == 0.0:
                continue
            variant_stats = compute_strategy_stats(fold_frame, variant_column)
            fold_rows.append(
                {
                    "variant": variant_name,
                    "monitoring_scope": "side_probe_only",
                    "tolerance": tolerance,
                    "fold": fold_name,
                    "test_start": fold_tuple[3]["date"].iloc[0].strftime("%Y-%m-%d"),
                    "test_end": fold_tuple[3]["date"].iloc[-1].strftime("%Y-%m-%d"),
                    "selected_rows": int(variant_stats["selected_rows"]),
                    "episode_count": int(variant_stats["episode_count"]),
                    "episode_hit_rate": round(float(variant_stats["episode_hit_rate"]), 4),
                    "episode_avg_return": round(float(variant_stats["episode_avg_return"]), 4),
                    "episode_max_drawdown_compound": round(float(variant_stats["episode_max_drawdown_compound"]), 4),
                }
            )

        full_oos_frame[variant_column] = full_oos_frame["shadow_selected_base"] | (
            full_oos_frame["pocket"] & (full_oos_frame["shadow_probability"] >= (full_oos_frame["shadow_cutoff"] - tolerance))
        )

        base_mask = (
            full_oos_frame["live_selected"] & (~full_oos_frame["shadow_selected_base"]) & full_oos_frame["pocket"]
        )
        recovered_mask = base_mask & full_oos_frame[variant_column]
        recovered_cases = full_oos_frame[recovered_mask].copy()
        for _, row in recovered_cases.iterrows():
            recovery_rows.append(
                {
                    "variant": variant_name,
                    "tolerance": tolerance,
                    "date": row["date"].strftime("%Y-%m-%d"),
                    "future_return_60": round(float(row["future_return_60"]), 4),
                    "live_probability": round(float(row["live_probability"]), 4),
                    "live_cutoff": round(float(row["live_cutoff"]), 4),
                    "shadow_probability": round(float(row["shadow_probability"]), 4),
                    "shadow_cutoff": round(float(row["shadow_cutoff"]), 4),
                    "shadow_gap": round(float(row["shadow_gap"]), 6),
                    "above_200dma_flag": int(row["above_200dma_flag"]),
                    "slope_60": round(float(row["slope_60"]), 6),
                }
            )

    summary_rows = [
        summarize_variant(
            "shadow_base" if tolerance == 0.0 else f"shadow_tol_{str(tolerance).replace('.', '_')}",
            full_oos_frame,
            fold_frames,
            tolerance,
        )
        for tolerance in TOLERANCE_VARIANTS
    ]

    pd.DataFrame(summary_rows).to_csv(get_summary_path(), sep="\t", index=False)
    pd.DataFrame(fold_rows).to_csv(get_fold_path(), sep="\t", index=False)
    recovery_table = pd.DataFrame(
        recovery_rows,
        columns=[
            "variant",
            "tolerance",
            "date",
            "future_return_60",
            "live_probability",
            "live_cutoff",
            "shadow_probability",
            "shadow_cutoff",
            "shadow_gap",
            "above_200dma_flag",
            "slope_60",
        ],
    )
    if not recovery_table.empty:
        recovery_table = recovery_table.sort_values(["variant", "date"]).reset_index(drop=True)
    recovery_table.to_csv(get_recovery_path(), sep="\t", index=False)

    print(f"Saved: {get_summary_path()}")
    print(f"Saved: {get_fold_path()}")
    print(f"Saved: {get_recovery_path()}")
    print(f"Held-out fold anchor: {heldout_name}")


if __name__ == "__main__":
    main()
