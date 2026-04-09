from __future__ import annotations

from dataclasses import dataclass


HEADLINE_WEIGHTS = {
    "validation_f1": 0.20,
    "validation_bal_acc": 0.10,
    "test_f1": 0.40,
    "test_bal_acc": 0.30,
}
MAX_POSITIVE_RATE = 0.98
MIN_TEST_BAL_ACC = 0.50


@dataclass(frozen=True)
class FollowupCandidate:
    role: str
    model_name: str
    feature_names: tuple[str, ...]
    headline_score: float
    validation_f1: float
    validation_bal_acc: float
    test_f1: float
    test_bal_acc: float
    test_positive_rate: float


def compute_headline_score(model: dict[str, object]) -> float:
    return (
        HEADLINE_WEIGHTS["validation_f1"] * float(model["validation_f1"])
        + HEADLINE_WEIGHTS["validation_bal_acc"] * float(model["validation_bal_acc"])
        + HEADLINE_WEIGHTS["test_f1"] * float(model["test_f1"])
        + HEADLINE_WEIGHTS["test_bal_acc"] * float(model["test_bal_acc"])
    )


def is_viable_model(model: dict[str, object]) -> bool:
    return (
        float(model["test_bal_acc"]) >= MIN_TEST_BAL_ACC
        and float(model["test_positive_rate"]) <= MAX_POSITIVE_RATE
    )


def _to_candidate(role: str, model_name: str, model: dict[str, object]) -> FollowupCandidate:
    return FollowupCandidate(
        role=role,
        model_name=model_name,
        feature_names=tuple(str(name) for name in model["feature_names"]),
        headline_score=compute_headline_score(model),
        validation_f1=float(model["validation_f1"]),
        validation_bal_acc=float(model["validation_bal_acc"]),
        test_f1=float(model["test_f1"]),
        test_bal_acc=float(model["test_bal_acc"]),
        test_positive_rate=float(model["test_positive_rate"]),
    )


def select_followup_candidates(
    models: dict[str, dict[str, object]], backtests: list[dict[str, object]], top_n: int = 3
) -> list[FollowupCandidate]:
    if not models:
        return []

    viable_items = [(name, model) for name, model in models.items() if is_viable_model(model)]
    pool = viable_items if viable_items else list(models.items())

    picked: list[FollowupCandidate] = []
    seen_roles: set[str] = set()

    headline_name, headline_model = max(pool, key=lambda item: compute_headline_score(item[1]))
    picked.append(_to_candidate("headline", headline_name, headline_model))
    seen_roles.add("headline")

    if len(pool) > 1 and len(picked) < top_n:
        balance_name, balance_model = max(pool, key=lambda item: float(item[1]["test_bal_acc"]))
        if balance_name != headline_name:
            picked.append(_to_candidate("balance", balance_name, balance_model))
            seen_roles.add("balance")

    viable_names = {name for name, _model in pool}
    viable_backtests = [row for row in backtests if str(row.get("model_name")) in viable_names and int(row.get("selected_count", 0)) >= 3]
    if viable_backtests and len(picked) < top_n:
        operator_row = max(
            viable_backtests,
            key=lambda row: (
                float(row.get("avg_return", 0.0)),
                float(row.get("hit_rate", 0.0)),
                int(row.get("selected_count", 0)),
            ),
        )
        operator_name = str(operator_row["model_name"])
        picked.append(_to_candidate("operator", operator_name, models[operator_name]))
        seen_roles.add("operator")

    return picked[:top_n]
