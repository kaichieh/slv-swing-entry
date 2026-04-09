from __future__ import annotations

from dataclasses import dataclass

import asset_followup as af
import prepare as pr


ROUND4_ADDON_FEATURES = (
    "rs_vs_benchmark_60",
    "ret_20_vs_benchmark",
    "ret_60_vs_benchmark",
    "price_ratio_benchmark_z_20",
    "price_ratio_benchmark_z_60",
    "atr_pct_20_percentile",
    "trend_quality_20",
    "distance_from_60d_low",
    "distance_from_120d_low",
)
ROLE_PRIORITY = {"headline": 0, "balance": 1, "operator": 2}
ADDON_PRIORITY = {name: idx for idx, name in enumerate(ROUND4_ADDON_FEATURES)}


@dataclass(frozen=True)
class Round4Spec:
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


def _candidate_neg_weight(candidate: af.FollowupCandidate) -> float | None:
    if candidate.test_positive_rate >= 0.99:
        return 1.60
    if candidate.test_positive_rate >= 0.95:
        return 1.45
    if candidate.test_positive_rate >= 0.80:
        return 1.30
    if candidate.test_positive_rate >= 0.65:
        return 1.15
    return None


def build_round4_specs(candidates: list[af.FollowupCandidate]) -> list[Round4Spec]:
    specs: list[Round4Spec] = []
    seen: set[str] = set()
    available_addons = tuple(name for name in ROUND4_ADDON_FEATURES if name in pr.EXPERIMENTAL_FEATURE_COLUMNS)

    for candidate in candidates:
        base_extras = _infer_extras(candidate.feature_names)
        candidate_neg_weight = _candidate_neg_weight(candidate)

        direct = Round4Spec(
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
            spec = Round4Spec(
                role=candidate.role,
                parent_model_name=candidate.model_name,
                name=_compose_name(extras, candidate_neg_weight),
                extra_features=extras,
                neg_weight=candidate_neg_weight,
            )
            if spec.name not in seen:
                specs.append(spec)
                seen.add(spec.name)

        benchmark_addons = tuple(
            name for name in ("rs_vs_benchmark_60", "price_ratio_benchmark_z_20", "price_ratio_benchmark_z_60") if name in available_addons
        )
        if benchmark_addons:
            extras = tuple(dict.fromkeys(base_extras + benchmark_addons))
            combo = Round4Spec(
                role=candidate.role,
                parent_model_name=candidate.model_name,
                name=_compose_name(extras, candidate_neg_weight),
                extra_features=extras,
                neg_weight=candidate_neg_weight,
            )
            if combo.name not in seen:
                specs.append(combo)
                seen.add(combo.name)

    return specs


def prioritize_round4_specs(specs: list[Round4Spec], limit: int = 12) -> list[Round4Spec]:
    benchmark_names = {"rs_vs_benchmark_60", "ret_20_vs_benchmark", "ret_60_vs_benchmark", "price_ratio_benchmark_z_20", "price_ratio_benchmark_z_60"}

    def sort_key(spec: Round4Spec) -> tuple[int, int, int, int, str]:
        addon_count = len(spec.extra_features)
        benchmark_count = sum(1 for name in spec.extra_features if name in benchmark_names)
        added = [name for name in spec.extra_features if name in ADDON_PRIORITY]
        best_addon_rank = min((ADDON_PRIORITY[name] for name in added), default=-1)
        return (
            ROLE_PRIORITY.get(spec.role, 9),
            0 if benchmark_count > 0 else 1,
            0 if addon_count <= 6 else 1,
            best_addon_rank,
            spec.name,
        )

    return sorted(specs, key=sort_key)[:limit]


def compute_round4_score(
    headline_score: float,
    walkforward_avg_test_bal_acc: float,
    operator_avg_return: float,
    operator_trade_count: int,
    test_positive_rate: float,
) -> float:
    trade_bonus = min(operator_trade_count, 20) / 200.0
    positive_rate_penalty = max(test_positive_rate - 0.75, 0.0) * 0.80
    return headline_score + 0.35 * walkforward_avg_test_bal_acc + operator_avg_return + trade_bonus - positive_rate_penalty
