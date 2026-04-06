from __future__ import annotations

import json
from dataclasses import dataclass

import asset_config as ac


@dataclass(frozen=True)
class ResearchProfile:
    asset_key: str
    asset_lane: str
    label_families: tuple[str, ...]
    default_feature_pool: tuple[str, ...]
    validation_policy: str
    reference_baseline: str
    adoption_thresholds: dict[str, float]


def load_research_profile(asset_key: str) -> ResearchProfile:
    payload = json.loads(ac.get_research_profile_path(asset_key).read_text(encoding="utf-8"))
    return ResearchProfile(
        asset_key=str(payload["asset_key"]),
        asset_lane=str(payload["asset_lane"]),
        label_families=tuple(str(item) for item in payload["label_families"]),
        default_feature_pool=tuple(str(item) for item in payload["default_feature_pool"]),
        validation_policy=str(payload["validation_policy"]),
        reference_baseline=str(payload["reference_baseline"]),
        adoption_thresholds={str(key): float(value) for key, value in payload["adoption_thresholds"].items()},
    )


def load_all_research_profiles() -> dict[str, ResearchProfile]:
    return {asset_key: load_research_profile(asset_key) for asset_key in ac.ASSET_DEFAULTS}
