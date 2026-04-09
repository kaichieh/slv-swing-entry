from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import asset_config as ac
import asset_followup as af
import prepare as pr
import research_batch as rb


FOLLOWUP_RULES = (
    "threshold",
    "fixed_0.47",
    "fixed_0.49",
    "top_10pct",
    "top_12_5pct",
    "top_15pct",
    "top_17_5pct",
    "top_20pct",
)
RECENT_WINDOW = 60


def candidate_validation_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "candidate_validation_summary.tsv"


def candidate_walkforward_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "candidate_walkforward_summary.tsv"


def operator_rule_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "operator_rule_summary.tsv"


def operator_preference_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "operator_preference_summary.tsv"


def operator_usage_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "operator_usage_summary.tsv"


def operator_decision_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "operator_decision_summary.tsv"


def round_float(value: float) -> float:
    return round(float(value), 4)


def parse_neg_weight(model_name: str) -> float:
    if "neg_weight_1_15" in model_name:
        return 1.15
    if "neg_weight_1_1" in model_name:
        return 1.10
    return pr.get_env_float("AR_NEG_WEIGHT", 1.0)


def parse_extra_interactions(model_name: str) -> tuple[tuple[str, str], ...]:
    if model_name.endswith("_interaction"):
        return (("ret_60", "sma_gap_60"),)
    return ()


def infer_extra_features(feature_names: tuple[str, ...]) -> tuple[str, ...]:
    base = set(pr.FEATURE_COLUMNS)
    return tuple(name for name in feature_names if name not in base)


def load_research_batch() -> dict[str, object]:
    path = ac.get_research_batch_path()
    return json.loads(path.read_text(encoding="utf-8"))


def load_backtests() -> list[dict[str, object]]:
    path = ac.get_backtest_output_path()
    if not path.exists():
        return []
    return pd.read_csv(path, sep="\t").to_dict(orient="records")


def load_default_frame() -> pd.DataFrame:
    raw = pr.download_asset_prices()
    return rb.build_labeled_frame(raw)


def train_candidate(default_frame: pd.DataFrame, candidate: af.FollowupCandidate) -> tuple[rb.ModelResult, dict[str, object]]:
    extra_features = infer_extra_features(candidate.feature_names)
    neg_weight = parse_neg_weight(candidate.model_name)
    extra_interactions = parse_extra_interactions(candidate.model_name)
    return rb.train_model(
        default_frame,
        candidate.model_name,
        extra_features=extra_features,
        neg_weight=neg_weight,
        extra_interactions=extra_interactions,
    )


def build_candidate_validation_table(candidates: list[af.FollowupCandidate]) -> pd.DataFrame:
    rows = []
    for row in candidates:
        rows.append(
            {
                "asset_key": ac.get_asset_key(),
                "role": row.role,
                "model_name": row.model_name,
                "extra_features": ",".join(infer_extra_features(row.feature_names)),
                "validation_f1": round_float(row.validation_f1),
                "validation_bal_acc": round_float(row.validation_bal_acc),
                "test_f1": round_float(row.test_f1),
                "test_bal_acc": round_float(row.test_bal_acc),
                "test_positive_rate": round_float(row.test_positive_rate),
                "headline_score": round_float(row.headline_score),
            }
        )
    return pd.DataFrame(rows)


def build_walkforward_table(default_frame: pd.DataFrame, candidates: list[af.FollowupCandidate]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for candidate in candidates:
        extra_features = infer_extra_features(candidate.feature_names)
        neg_weight = parse_neg_weight(candidate.model_name)
        for fold in rb.evaluate_walk_forward_with_folds(default_frame, extra_features, folds=4, neg_weight=neg_weight):
            rows.append(
                {
                    "asset_key": ac.get_asset_key(),
                    "role": candidate.role,
                    "model_name": candidate.model_name,
                    "extra_features": ",".join(extra_features),
                    "fold_name": fold.fold_name,
                    "validation_f1": round_float(fold.validation_f1),
                    "validation_bal_acc": round_float(fold.validation_bal_acc),
                    "test_f1": round_float(fold.test_f1),
                    "test_bal_acc": round_float(fold.test_bal_acc),
                    "test_positive_rate": round_float(fold.test_positive_rate),
                }
            )
    return pd.DataFrame(rows)


def build_operator_rule_table(default_frame: pd.DataFrame, candidates: list[af.FollowupCandidate]) -> tuple[pd.DataFrame, dict[str, object]]:
    rows: list[dict[str, object]] = []
    trained: dict[str, object] = {}
    for candidate in candidates:
        result, artifacts = train_candidate(default_frame, candidate)
        trained[candidate.model_name] = {"result": result, "artifacts": artifacts, "role": candidate.role}
        for rule_name in FOLLOWUP_RULES:
            for row in rb.rule_comparison_rows(candidate.model_name, artifacts, (rule_name,)):
                row["asset_key"] = ac.get_asset_key()
                row["role"] = candidate.role
                rows.append(row)
    return pd.DataFrame(rows), trained


def build_operator_preference_table(rule_table: pd.DataFrame) -> pd.DataFrame:
    table = rule_table.copy()
    table = table[table["selected_count"] >= 3].copy()
    if table.empty:
        return pd.DataFrame(
            columns=[
                "model_name",
                "rule_name",
                "role",
                "operator_score",
                "selected_count",
                "hit_rate",
                "avg_return",
                "cutoff",
            ]
        )
    table["operator_score"] = (
        table["avg_return"].astype(float) * 100.0
        + table["hit_rate"].astype(float) * 2.0
        + table["selected_count"].astype(float) / 20.0
    )
    table = table.sort_values(["operator_score", "avg_return", "hit_rate", "selected_count"], ascending=False)
    return table[
        [
            "model_name",
            "rule_name",
            "role",
            "operator_score",
            "selected_count",
            "hit_rate",
            "avg_return",
            "threshold_or_cutoff",
        ]
    ].rename(columns={"threshold_or_cutoff": "cutoff"})


def build_operator_usage_table(default_frame: pd.DataFrame, preference_table: pd.DataFrame, trained: dict[str, object]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    if preference_table.empty:
        return pd.DataFrame(
            columns=[
                "model_name",
                "rule_name",
                "recent_selected_count",
                "latest_date",
                "latest_score",
                "latest_selected",
                "cutoff",
                "last_selected_date",
            ]
        )
    for _, pref in preference_table.head(5).iterrows():
        model_name = str(pref["model_name"])
        artifacts = trained[model_name]["artifacts"]
        clean_frame = pd.concat(
            [
                artifacts["clean_splits"]["train"],
                artifacts["clean_splits"]["validation"],
                artifacts["clean_splits"]["test"],
            ],
            ignore_index=True,
        )
        feature_names = list(artifacts["feature_names"])
        probs = rb.score_frame(
            clean_frame,
            feature_names,
            artifacts["train_mean"],
            artifacts["train_std"],
            artifacts["pair_indices"],
            artifacts["weights"],
        )
        rule_name = str(pref["rule_name"])
        selected, cutoff = rb.classify_probs_by_rule(probs, float(artifacts["threshold"]), rule_name)
        recent = clean_frame.iloc[-RECENT_WINDOW:].copy().reset_index(drop=True)
        recent_probs = probs[-RECENT_WINDOW:]
        recent_selected = selected[-RECENT_WINDOW:]
        last_selected_date = ""
        if bool(recent_selected.any()):
            last_selected_date = recent.loc[recent_selected, "date"].iloc[-1].strftime("%Y-%m-%d")
        rows.append(
            {
                "model_name": model_name,
                "rule_name": rule_name,
                "role": pref["role"],
                "recent_selected_count": int(recent_selected.sum()),
                "latest_date": recent["date"].iloc[-1].strftime("%Y-%m-%d"),
                "latest_score": round_float(recent_probs[-1]),
                "latest_selected": bool(recent_selected[-1]),
                "cutoff": round_float(cutoff),
                "last_selected_date": last_selected_date,
            }
        )
    return pd.DataFrame(rows)


def build_operator_decision_table(preference_table: pd.DataFrame, usage_table: pd.DataFrame) -> pd.DataFrame:
    if preference_table.empty:
        return pd.DataFrame(
            columns=[
                "model_name",
                "rule_name",
                "role",
                "operator_score",
                "recent_selected_count",
                "latest_date",
                "latest_selected",
                "cutoff",
            ]
        )
    usage_map = {
        (str(row["model_name"]), str(row["rule_name"])): row
        for _, row in usage_table.iterrows()
    }
    rows = []
    for _, pref in preference_table.head(3).iterrows():
        usage = usage_map.get((str(pref["model_name"]), str(pref["rule_name"])))
        rows.append(
            {
                "model_name": pref["model_name"],
                "rule_name": pref["rule_name"],
                "role": pref["role"],
                "operator_score": round_float(pref["operator_score"]),
                "recent_selected_count": int(usage["recent_selected_count"]) if usage is not None else 0,
                "latest_date": usage["latest_date"] if usage is not None else "",
                "latest_selected": bool(usage["latest_selected"]) if usage is not None else False,
                "cutoff": float(usage["cutoff"]) if usage is not None else float(pref["cutoff"]),
            }
        )
    return pd.DataFrame(rows)


def save_table(table: pd.DataFrame, path: Path) -> None:
    table.to_csv(path, sep="\t", index=False)


def main() -> None:
    data = load_research_batch()
    candidates = af.select_followup_candidates(
        data["models"],
        load_backtests(),
        top_n=3,
    )
    default_frame = load_default_frame()

    validation_table = build_candidate_validation_table(candidates)
    walkforward_table = build_walkforward_table(default_frame, candidates)
    rule_table, trained = build_operator_rule_table(default_frame, candidates)
    preference_table = build_operator_preference_table(rule_table)
    usage_table = build_operator_usage_table(default_frame, preference_table, trained)
    decision_table = build_operator_decision_table(preference_table, usage_table)

    save_table(validation_table, candidate_validation_output_path())
    save_table(walkforward_table, candidate_walkforward_output_path())
    save_table(rule_table, operator_rule_output_path())
    save_table(preference_table, operator_preference_output_path())
    save_table(usage_table, operator_usage_output_path())
    save_table(decision_table, operator_decision_output_path())

    print(
        json.dumps(
            {
                "asset_key": ac.get_asset_key(),
                "candidate_count": len(validation_table),
                "operator_rows": len(rule_table),
                "preference_rows": len(preference_table),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
