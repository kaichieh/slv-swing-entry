from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import asset_config as ac
import asset_followup as af
import asset_followup_round4 as afr4
import prepare as pr
import research_batch as rb


RULES = (
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


def round4_validation_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "followup_round4_validation_summary.tsv"


def round4_operator_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "followup_round4_operator_summary.tsv"


def round4_decision_output_path(asset_key: str | None = None) -> Path:
    return ac.get_asset_dir(asset_key) / "followup_round4_decision_summary.tsv"


def round_float(value: float) -> float:
    return round(float(value), 4)


def load_round3_candidates() -> list[af.FollowupCandidate]:
    path = ac.get_asset_dir() / "followup_round3_validation_summary.tsv"
    if not path.exists():
        raise FileNotFoundError(f"Round-3 follow-up candidates not found at {path}")
    table = pd.read_csv(path, sep="\t")
    rows: list[af.FollowupCandidate] = []
    for _, row in table.iterrows():
        extras = tuple(part for part in str(row["extra_features"]).split(",") if part)
        feature_names = tuple(pr.FEATURE_COLUMNS) + extras
        rows.append(
            af.FollowupCandidate(
                role=str(row["role"]),
                model_name=str(row["model_name"]),
                feature_names=feature_names,
                headline_score=float(row["headline_score"]),
                validation_f1=float(row["validation_f1"]),
                validation_bal_acc=float(row["validation_bal_acc"]),
                test_f1=float(row["test_f1"]),
                test_bal_acc=float(row["test_bal_acc"]),
                test_positive_rate=float(row["test_positive_rate"]),
            )
        )
    return rows


def load_default_frame() -> pd.DataFrame:
    raw = pr.download_asset_prices()
    return rb.build_labeled_frame(raw)


def best_operator_row(rule_rows: list[dict[str, object]]) -> dict[str, object]:
    viable = [row for row in rule_rows if int(row["selected_count"]) >= 3]
    pool = viable if viable else rule_rows
    return max(
        pool,
        key=lambda row: (
            float(row["avg_return"]),
            float(row["hit_rate"]),
            int(row["selected_count"]),
        ),
    )


def build_recent_usage(
    clean_splits: dict[str, pd.DataFrame],
    full_probs: pd.Series | pd.Index | list[float],
    threshold: float,
    rule_name: str,
) -> dict[str, object]:
    frame = pd.concat(
        [clean_splits["train"], clean_splits["validation"], clean_splits["test"]],
        ignore_index=True,
    )
    probs_series = pd.Series(full_probs, dtype=float)
    selected, cutoff = rb.classify_probs_by_rule(probs_series.to_numpy(dtype=float), threshold, rule_name)
    recent = frame.iloc[-RECENT_WINDOW:].copy().reset_index(drop=True)
    recent_probs = probs_series.iloc[-RECENT_WINDOW:].reset_index(drop=True)
    recent_selected = pd.Series(selected[-RECENT_WINDOW:])
    last_selected_date = ""
    if bool(recent_selected.any()):
        last_selected_date = recent.loc[recent_selected, "date"].iloc[-1].strftime("%Y-%m-%d")
    return {
        "recent_selected_count": int(recent_selected.sum()),
        "latest_date": recent["date"].iloc[-1].strftime("%Y-%m-%d"),
        "latest_score": round_float(recent_probs.iloc[-1]),
        "latest_selected": bool(recent_selected.iloc[-1]),
        "cutoff": round_float(cutoff),
        "last_selected_date": last_selected_date,
    }


def main() -> None:
    candidates = load_round3_candidates()
    specs = afr4.prioritize_round4_specs(afr4.build_round4_specs(candidates), limit=12)
    default_frame = load_default_frame()

    validation_rows: list[dict[str, object]] = []
    operator_rows: list[dict[str, object]] = []
    decision_rows: list[dict[str, object]] = []

    for spec in specs:
        result, artifacts = rb.train_model(
            default_frame,
            spec.name,
            extra_features=spec.extra_features,
            neg_weight=spec.neg_weight,
        )
        effective_neg_weight = spec.neg_weight if spec.neg_weight is not None else pr.get_env_float("AR_NEG_WEIGHT", 1.0)
        walkforward = rb.evaluate_walk_forward_with_folds(
            default_frame,
            spec.extra_features,
            folds=4,
            neg_weight=effective_neg_weight,
        )
        wf_avg = sum(row.test_bal_acc for row in walkforward) / len(walkforward) if walkforward else 0.0

        spec_rule_rows: list[dict[str, object]] = []
        for rule in RULES:
            spec_rule_rows.extend(rb.rule_comparison_rows(spec.name, artifacts, (rule,)))
        best_rule = best_operator_row(spec_rule_rows)
        full_clean_frame = pd.concat(
            [
                artifacts["clean_splits"]["train"],
                artifacts["clean_splits"]["validation"],
                artifacts["clean_splits"]["test"],
            ],
            ignore_index=True,
        )
        full_probs = rb.score_frame(
            full_clean_frame,
            list(artifacts["feature_names"]),
            artifacts["train_mean"],
            artifacts["train_std"],
            artifacts["pair_indices"],
            artifacts["weights"],
        )
        usage = build_recent_usage(
            artifacts["clean_splits"],
            full_probs.tolist(),
            float(artifacts["threshold"]),
            str(best_rule["rule_name"]),
        )
        headline_score = af.compute_headline_score(
            {
                "validation_f1": result.validation_f1,
                "validation_bal_acc": result.validation_bal_acc,
                "test_f1": result.test_f1,
                "test_bal_acc": result.test_bal_acc,
            }
        )
        round4_score = afr4.compute_round4_score(
            headline_score=headline_score,
            walkforward_avg_test_bal_acc=wf_avg,
            operator_avg_return=float(best_rule["avg_return"]),
            operator_trade_count=int(best_rule["selected_count"]),
            test_positive_rate=float(result.test_positive_rate),
        )

        validation_rows.append(
            {
                "asset_key": ac.get_asset_key(),
                "role": spec.role,
                "parent_model_name": spec.parent_model_name,
                "model_name": spec.name,
                "extra_features": ",".join(spec.extra_features),
                "neg_weight": "" if spec.neg_weight is None else spec.neg_weight,
                "validation_f1": round_float(result.validation_f1),
                "validation_bal_acc": round_float(result.validation_bal_acc),
                "test_f1": round_float(result.test_f1),
                "test_bal_acc": round_float(result.test_bal_acc),
                "test_positive_rate": round_float(result.test_positive_rate),
                "headline_score": round_float(headline_score),
                "walkforward_avg_test_bal_acc": round_float(wf_avg),
                "round4_score": round_float(round4_score),
            }
        )
        operator_rows.append(
            {
                "asset_key": ac.get_asset_key(),
                "role": spec.role,
                "model_name": spec.name,
                "best_rule_name": best_rule["rule_name"],
                "selected_count": int(best_rule["selected_count"]),
                "hit_rate": round_float(best_rule["hit_rate"]),
                "avg_return": round_float(best_rule["avg_return"]),
                "cutoff": round_float(best_rule["threshold_or_cutoff"]),
                "recent_selected_count": usage["recent_selected_count"],
                "latest_date": usage["latest_date"],
                "latest_score": usage["latest_score"],
                "latest_selected": usage["latest_selected"],
                "last_selected_date": usage["last_selected_date"],
            }
        )

    validation_table = pd.DataFrame(validation_rows).sort_values("round4_score", ascending=False)
    operator_table = pd.DataFrame(operator_rows)
    operator_map = {str(row["model_name"]): row for _, row in operator_table.iterrows()}
    for _, row in validation_table.head(3).iterrows():
        operator = operator_map[str(row["model_name"])]
        decision_rows.append(
            {
                "asset_key": ac.get_asset_key(),
                "role": row["role"],
                "model_name": row["model_name"],
                "round4_score": row["round4_score"],
                "walkforward_avg_test_bal_acc": row["walkforward_avg_test_bal_acc"],
                "test_positive_rate": row["test_positive_rate"],
                "best_rule_name": operator["best_rule_name"],
                "best_rule_avg_return": operator["avg_return"],
                "best_rule_trade_count": operator["selected_count"],
                "recent_selected_count": operator["recent_selected_count"],
                "latest_selected": operator["latest_selected"],
            }
        )
    decision_table = pd.DataFrame(decision_rows)

    validation_table.to_csv(round4_validation_output_path(), sep="\t", index=False)
    operator_table.to_csv(round4_operator_output_path(), sep="\t", index=False)
    decision_table.to_csv(round4_decision_output_path(), sep="\t", index=False)

    print(
        json.dumps(
            {
                "asset_key": ac.get_asset_key(),
                "round4_specs": len(validation_table),
                "top_model": validation_table.iloc[0]["model_name"] if len(validation_table) else "",
                "top_score": float(validation_table.iloc[0]["round4_score"]) if len(validation_table) else 0.0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
