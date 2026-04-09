from __future__ import annotations

from dataclasses import dataclass

import asset_followup as af
import prepare as pr


ROUND2_ADDON_FEATURES = (
    "atr_pct_20",
    "distance_to_252_high",
    "close_location_20",
    "up_day_ratio_20",
    "above_200dma_flag",
    "rolling_vol_60",
    "rolling_return_120",
    "sma_gap_120",
    "ret_60",
    "sma_gap_60",
)
ROLE_PRIORITY = {"headline": 0, "balance": 1, "operator": 2}
ADDON_PRIORITY = {name: idx for idx, name in enumerate(ROUND2_ADDON_FEATURES)}


@dataclass(frozen=True)
class Round2Spec:
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


def build_round2_specs(candidates: list[af.FollowupCandidate]) -> list[Round2Spec]:
    specs: list[Round2Spec] = []
    seen: set[str] = set()
    for candidate in candidates:
        base_extras = _infer_extras(candidate.feature_names)
        candidate_neg_weight = 1.15 if {"ret_60", "sma_gap_60"}.issubset(set(base_extras)) else None

        direct = Round2Spec(
            role=candidate.role,
            parent_model_name=candidate.model_name,
            name=_compose_name(base_extras, candidate_neg_weight),
            extra_features=base_extras,
            neg_weight=candidate_neg_weight,
        )
        if direct.name not in seen:
            specs.append(direct)
            seen.add(direct.name)

        for addon in ROUND2_ADDON_FEATURES:
            if addon in base_extras:
                continue
            extras = tuple(dict.fromkeys(base_extras + (addon,)))
            neg_weight = 1.15 if {"ret_60", "sma_gap_60"}.issubset(set(extras)) else None
            spec = Round2Spec(
                role=candidate.role,
                parent_model_name=candidate.model_name,
                name=_compose_name(extras, neg_weight),
                extra_features=extras,
                neg_weight=neg_weight,
            )
            if spec.name not in seen:
                specs.append(spec)
                seen.add(spec.name)
    return specs


def prioritize_round2_specs(specs: list[Round2Spec], limit: int = 8) -> list[Round2Spec]:
    def sort_key(spec: Round2Spec) -> tuple[int, int, int, str]:
        addon_count = len(spec.extra_features)
        added = [name for name in spec.extra_features if name in ADDON_PRIORITY]
        best_addon_rank = min((ADDON_PRIORITY[name] for name in added), default=-1)
        return (
            ROLE_PRIORITY.get(spec.role, 9),
            0 if addon_count <= 2 else 1,
            best_addon_rank,
            spec.name,
        )

    return sorted(specs, key=sort_key)[:limit]


def compute_round2_score(
    headline_score: float,
    walkforward_avg_test_bal_acc: float,
    operator_avg_return: float,
    operator_trade_count: int,
) -> float:
    trade_bonus = min(operator_trade_count, 20) / 200.0
    return headline_score + 0.30 * walkforward_avg_test_bal_acc + operator_avg_return + trade_bonus
