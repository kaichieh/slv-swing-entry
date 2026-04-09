from __future__ import annotations

from dataclasses import dataclass

import asset_followup as af
import prepare as pr


ROUND3_ADDON_FEATURES = (
    "atr_pct_20_percentile",
    "slope_20",
    "slope_60",
    "trend_quality_20",
    "percent_up_days_20",
    "percent_up_days_60",
    "bollinger_bandwidth_20",
    "vol_ratio_20_120",
    "distance_from_60d_low",
    "distance_from_120d_low",
    "rs_vs_benchmark_60",
    "ret_20_vs_benchmark",
    "ret_60_vs_benchmark",
    "price_ratio_benchmark_z_20",
    "price_ratio_benchmark_z_60",
)
ROLE_PRIORITY = {"headline": 0, "balance": 1, "operator": 2}
ADDON_PRIORITY = {name: idx for idx, name in enumerate(ROUND3_ADDON_FEATURES)}


@dataclass(frozen=True)
class Round3Spec:
    role: str
    parent_model_name: str
    name: str
    extra_features: tuple[str, ...]
    neg_weight: float | None = None


def _infer_extras(feature_names: tuple[str, ...]) -> tuple[str, ...]:
    base = set(pr.FEATURE_COLUMNS)
    return tuple(name for name in feature_names if name not in base)


def _compose_name(extra_features: tuple[str, ...], neg_weight: float | None) -> str:
    if not extra_features:
        name = "baseline"
    elif len(extra_features) == 1:
        name = extra_features[0]
    else:
        name = "_plus_".join(extra_features)
    if neg_weight is not None:
        suffix = str(neg_weight).replace(".", "_")
        return f"{name}_plus_neg_weight_{suffix}"
    return name


def _candidate_neg_weight(candidate: af.FollowupCandidate, base_extras: tuple[str, ...]) -> float | None:
    if candidate.test_positive_rate >= 0.90:
        return 1.30
    if candidate.test_positive_rate >= 0.75:
        return 1.15
    if {"ret_60", "sma_gap_60"}.issubset(set(base_extras)):
        return 1.15
    return None


def build_round3_specs(candidates: list[af.FollowupCandidate]) -> list[Round3Spec]:
    specs: list[Round3Spec] = []
    seen: set[str] = set()
    available_addons = tuple(name for name in ROUND3_ADDON_FEATURES if name in pr.EXPERIMENTAL_FEATURE_COLUMNS)

    for candidate in candidates:
        base_extras = _infer_extras(candidate.feature_names)
        candidate_neg_weight = _candidate_neg_weight(candidate, base_extras)

        direct = Round3Spec(
            role=candidate.role,
            parent_model_name=candidate.model_name,
            name=_compose_name(base_extras, candidate_neg_weight),
            extra_features=base_extras,
            neg_weight=candidate_neg_weight,
        )
        if direct.name not in seen:
            specs.append(direct)
            seen.add(direct.name)

        for addon in available_addons:
            if addon in base_extras:
                continue
            extras = tuple(dict.fromkeys(base_extras + (addon,)))
            spec = Round3Spec(
                role=candidate.role,
                parent_model_name=candidate.model_name,
                name=_compose_name(extras, candidate_neg_weight),
                extra_features=extras,
                neg_weight=candidate_neg_weight,
            )
            if spec.name not in seen:
                specs.append(spec)
                seen.add(spec.name)

        if candidate.test_positive_rate >= 0.90:
            guarded = Round3Spec(
                role=candidate.role,
                parent_model_name=candidate.model_name,
                name=_compose_name(base_extras, 1.45),
                extra_features=base_extras,
                neg_weight=1.45,
            )
            if guarded.name not in seen:
                specs.append(guarded)
                seen.add(guarded.name)

    return specs


def prioritize_round3_specs(specs: list[Round3Spec], limit: int = 10) -> list[Round3Spec]:
    def sort_key(spec: Round3Spec) -> tuple[int, int, int, int, str]:
        addon_count = len(spec.extra_features)
        added = [name for name in spec.extra_features if name in ADDON_PRIORITY]
        best_addon_rank = min((ADDON_PRIORITY[name] for name in added), default=-1)
        return (
            ROLE_PRIORITY.get(spec.role, 9),
            0 if addon_count <= 3 else 1,
            0 if spec.neg_weight is not None else 1,
            best_addon_rank,
            spec.name,
        )

    return sorted(specs, key=sort_key)[:limit]


def compute_round3_score(
    headline_score: float,
    walkforward_avg_test_bal_acc: float,
    operator_avg_return: float,
    operator_trade_count: int,
    test_positive_rate: float,
) -> float:
    trade_bonus = min(operator_trade_count, 20) / 200.0
    positive_rate_penalty = max(test_positive_rate - 0.85, 0.0) * 0.40
    return headline_score + 0.35 * walkforward_avg_test_bal_acc + operator_avg_return + trade_bonus - positive_rate_penalty
