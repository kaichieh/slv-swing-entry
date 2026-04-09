from __future__ import annotations

import argparse
from pathlib import Path

import asset_config as ac
import batch_research_config as brc


def build_program_text(symbol: str, bucket: str, defaults: ac.AssetDefaults) -> str:
    return "\n".join(
        [
            f"# {symbol} Program",
            "",
            f"This asset is part of the cross-asset batch universe under the `{bucket}` bucket.",
            "",
            "## Current Research Direction",
            "",
            f"- baseline reference: `{defaults.horizon_days}d +{defaults.upper_barrier:.0%}/{defaults.lower_barrier:.0%} {defaults.label_mode}`",
            "- establish a clean baseline before trying asset-specific feature ideas",
            "- compare this line against the rest of the first-round universe for predictability and stability",
            "",
            "## Working Style",
            "",
            "1. Keep the active research backlog in `task.md`.",
            "2. Save every completed run in `results.tsv`.",
            "3. Keep future follow-up ideas in `ideas.md` until they become concrete backlog items.",
            "",
        ]
    )


def build_task_text(symbol: str, defaults: ac.AssetDefaults) -> str:
    return "\n".join(
        [
            f"# {symbol} Backlog",
            "",
            "## First Round",
            "",
            f"- [ ] Run `AR_ASSET={symbol.lower()} python prepare.py` and confirm dataset shape.",
            f"- [ ] Run `AR_ASSET={symbol.lower()} python train.py` and capture baseline metrics.",
            f"- [ ] Run `AR_ASSET={symbol.lower()} python predict_latest.py` for the baseline live snapshot.",
            f"- [ ] Run `AR_ASSET={symbol.lower()} python chart_signals.py` and confirm chart output.",
            f"- [ ] Write the baseline row into `assets/{symbol.lower()}/results.tsv`.",
            "",
            "## Notes",
            "",
            f"- Default label config: `{defaults.horizon_days}d +{defaults.upper_barrier:.0%}/{defaults.lower_barrier:.0%} {defaults.label_mode}`.",
            "- This asset was scaffolded from the cross-asset first-round batch universe.",
            "",
        ]
    )


def build_ideas_text(symbol: str) -> str:
    return "\n".join(
        [
            f"# {symbol} Ideas",
            "",
            "- compare nearby label widths if the baseline is too imbalanced",
            "- test one or two simple momentum features before broader sweeps",
            "- compare threshold and top-percentile rules after the first stable candidate appears",
            "",
        ]
    )


def ensure_results_file(path: Path) -> None:
    if path.exists():
        return
    path.write_text(
        "commit_id\tvalidation_f1\tvalidation_accuracy\tvalidation_bal_acc\ttest_f1\ttest_accuracy\ttest_bal_acc\theadline_score\tpromotion_gate\tstatus\tdescription\n",
        encoding="utf-8",
    )


def scaffold_candidate(candidate: brc.BatchCandidate) -> Path:
    defaults = ac.ASSET_DEFAULTS[candidate.asset_key]
    asset_dir = ac.get_asset_dir(candidate.asset_key)
    asset_dir.mkdir(parents=True, exist_ok=True)
    (asset_dir / "config.json").write_text(
        "\n".join(
            [
                "{",
                f'  "asset_key": "{candidate.asset_key}",',
                f'  "symbol": "{candidate.symbol}",',
                f'  "horizon_days": {defaults.horizon_days},',
                f'  "upper_barrier": {defaults.upper_barrier},',
                f'  "lower_barrier": {defaults.lower_barrier},',
                f'  "label_mode": "{defaults.label_mode}"',
                "}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    (asset_dir / "program.md").write_text(build_program_text(candidate.symbol, candidate.bucket, defaults), encoding="utf-8")
    (asset_dir / "task.md").write_text(build_task_text(candidate.symbol, defaults), encoding="utf-8")
    (asset_dir / "ideas.md").write_text(build_ideas_text(candidate.symbol), encoding="utf-8")
    ensure_results_file(asset_dir / "results.tsv")
    return asset_dir


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate asset scaffolds for the first batch-research round.")
    parser.add_argument("--config", default=brc.DEFAULT_BATCH_CONFIG_NAME, help="Batch config name without .json")
    parser.add_argument("--round-size", type=int, default=None, help="Override first-round target count")
    args = parser.parse_args()

    config = brc.load_batch_research_config(args.config)
    candidates = brc.get_round_candidates(config, args.round_size)
    for candidate in candidates:
        scaffold_candidate(candidate)
        print(candidate.asset_key)


if __name__ == "__main__":
    main()
