from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import re


REPO_DIR = Path(__file__).resolve().parent
BATCH_CONFIG_DIR = REPO_DIR / "batch_configs"
DEFAULT_BATCH_CONFIG_NAME = "cross_asset_100"


@dataclass(frozen=True)
class BatchCandidate:
    asset_key: str
    symbol: str
    bucket: str


@dataclass(frozen=True)
class BatchResearchConfig:
    name: str
    template_asset_key: str
    research_goal: str
    first_round_size: int
    candidates: tuple[BatchCandidate, ...]


def get_batch_research_config_path(name: str = DEFAULT_BATCH_CONFIG_NAME) -> Path:
    return BATCH_CONFIG_DIR / f"{name}.json"


def load_batch_research_config(name: str = DEFAULT_BATCH_CONFIG_NAME) -> BatchResearchConfig:
    payload = json.loads(get_batch_research_config_path(name).read_text(encoding="utf-8"))
    candidates = tuple(
        BatchCandidate(
            asset_key=str(row.get("asset_key") or normalize_asset_key(str(row["symbol"]))),
            symbol=str(row["symbol"]),
            bucket=str(row["bucket"]),
        )
        for row in payload["candidates"]
    )
    return BatchResearchConfig(
        name=str(payload["name"]),
        template_asset_key=str(payload["template_asset_key"]),
        research_goal=str(payload["research_goal"]),
        first_round_size=int(payload.get("first_round_size", 20)),
        candidates=candidates,
    )


def normalize_asset_key(symbol: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "_", symbol.strip().lower())
    return cleaned.strip("_")


def get_round_candidates(
    config: BatchResearchConfig,
    round_size: int | None = None,
) -> tuple[BatchCandidate, ...]:
    target_count = round_size or config.first_round_size
    return config.candidates[:target_count]


def render_task_markdown(config: BatchResearchConfig, round_size: int | None = None) -> str:
    first_round_size = round_size or config.first_round_size
    lines = [
        "# Cross-Asset Batch Research",
        "",
        f"Research goal: {config.research_goal}",
        f"Template asset folder: `assets/{config.template_asset_key}`",
        f"First round target count: `{first_round_size}`",
        "",
        "## First Round Targets",
        "",
    ]
    for candidate in config.candidates[:first_round_size]:
        lines.append(f"- [ ] `{candidate.symbol}`")
    lines.extend(
        [
            "",
            "## Full Universe",
            "",
        ]
    )
    current_bucket = ""
    for candidate in config.candidates:
        if candidate.bucket != current_bucket:
            current_bucket = candidate.bucket
            lines.extend(["", f"### {current_bucket}", ""])
        lines.append(f"- [ ] `{candidate.symbol}`")
    lines.append("")
    return "\n".join(lines)
