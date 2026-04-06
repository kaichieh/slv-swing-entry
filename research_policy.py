from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GateDecision:
    viability: str
    improvement: str
    adoption: str
    summary: str


POLICIES: dict[str, dict[str, float]] = {
    "momentum_default": {
        "max_positive_rate": 0.85,
        "min_rows": 1200,
        "min_walkforward_bal_acc": 0.51,
        "min_recent_consistency": 0.65,
        "min_trade_count": 10,
        "max_drawdown_pct": 0.15,
    },
    "macro_default": {
        "max_positive_rate": 0.75,
        "min_rows": 1500,
        "min_walkforward_bal_acc": 0.50,
        "min_recent_consistency": 0.60,
        "min_trade_count": 12,
        "max_drawdown_pct": 0.12,
    },
    "index_default": {
        "max_positive_rate": 0.70,
        "min_rows": 1800,
        "min_walkforward_bal_acc": 0.52,
        "min_recent_consistency": 0.62,
        "min_trade_count": 14,
        "max_drawdown_pct": 0.10,
    },
    "sector_default": {
        "max_positive_rate": 0.75,
        "min_rows": 1500,
        "min_walkforward_bal_acc": 0.51,
        "min_recent_consistency": 0.60,
        "min_trade_count": 12,
        "max_drawdown_pct": 0.12,
    },
}


def evaluate_policy(policy_name: str, metrics: dict[str, float]) -> GateDecision:
    policy = POLICIES[policy_name]

    viability = "viable"
    if metrics["rows"] < policy["min_rows"] or metrics["positive_rate"] > policy["max_positive_rate"]:
        viability = "not_viable"
    elif metrics["walkforward_median_bal_acc"] < policy["min_walkforward_bal_acc"]:
        viability = "viable_with_caution"

    improvement = "improvement_confirmed"
    if viability == "not_viable":
        improvement = "no_durable_improvement"
    elif metrics["recent_consistency"] < policy["min_recent_consistency"]:
        improvement = "research_only_improvement"

    adoption = "adopt"
    if (
        viability != "viable"
        or improvement != "improvement_confirmed"
        or metrics["trade_count"] < policy["min_trade_count"]
        or metrics["max_drawdown_pct"] > policy["max_drawdown_pct"]
    ):
        adoption = "keep_as_research_primary"
    if viability == "not_viable":
        adoption = "archive_reference_only"

    return GateDecision(
        viability=viability,
        improvement=improvement,
        adoption=adoption,
        summary=f"{policy_name}:{viability}:{improvement}:{adoption}",
    )
