from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AssetDefaults:
    key: str
    symbol: str
    upper_barrier: float
    lower_barrier: float
    horizon_days: int
    label_mode: str


DEFAULT_ASSET_KEY = "slv"
ASSET_DEFAULTS: dict[str, AssetDefaults] = {
    "slv": AssetDefaults("slv", "SLV", 0.08, -0.04, 60, "drop-neutral"),
    "qqq": AssetDefaults("qqq", "QQQ", 0.08, -0.04, 60, "drop-neutral"),
    "nvda": AssetDefaults("nvda", "NVDA", 0.12, -0.06, 60, "drop-neutral"),
    "tsla": AssetDefaults("tsla", "TSLA", 0.12, -0.06, 60, "drop-neutral"),
}

REPO_DIR = Path(__file__).resolve().parent
ASSETS_DIR = REPO_DIR / "assets"


def get_asset_key() -> str:
    candidate = os.getenv("AR_ASSET", DEFAULT_ASSET_KEY).strip().lower()
    if candidate not in ASSET_DEFAULTS:
        raise ValueError(f"Unsupported AR_ASSET '{candidate}'. Known assets: {', '.join(sorted(ASSET_DEFAULTS))}")
    return candidate


def get_asset_dir(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    return ASSETS_DIR / key


def load_asset_config(asset_key: str | None = None) -> dict[str, object]:
    key = asset_key or get_asset_key()
    defaults = ASSET_DEFAULTS[key]
    config_path = get_asset_dir(key) / "config.json"
    config: dict[str, object] = {
        "asset_key": defaults.key,
        "symbol": defaults.symbol,
        "upper_barrier": defaults.upper_barrier,
        "lower_barrier": defaults.lower_barrier,
        "horizon_days": defaults.horizon_days,
        "label_mode": defaults.label_mode,
    }
    if config_path.exists():
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        config.update(loaded)
    return config


def get_asset_symbol(asset_key: str | None = None) -> str:
    return str(load_asset_config(asset_key)["symbol"])


def get_cache_dir(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    return REPO_DIR / ".cache" / f"{key}-swing-entry"


def get_raw_data_path(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    return get_cache_dir(key) / f"{key}_daily.csv"


def get_processed_data_path(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    return get_cache_dir(key) / f"{key}_features.csv"


def get_metadata_path(asset_key: str | None = None) -> Path:
    return get_cache_dir(asset_key) / "metadata.json"


def get_chart_output_path(asset_key: str | None = None) -> Path:
    return get_cache_dir(asset_key) / "signal_chart.html"


def get_research_batch_path(asset_key: str | None = None) -> Path:
    return get_cache_dir(asset_key) / "research_batch.json"


def get_exit_round_path(asset_key: str | None = None) -> Path:
    return get_cache_dir(asset_key) / "exit_round1.json"


def get_results_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "results.tsv"


def get_task_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "task.md"


def get_ideas_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "ideas.md"


def get_program_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "program.md"


def get_backtest_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "backtest_comparison.tsv"


def get_regime_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regime_summary.tsv"


def get_signal_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "signal_bucket_summary.tsv"


def get_forward_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "forward_trade_summary.tsv"


def get_rule_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "rule_comparison.tsv"


def get_regression_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regression_summary.tsv"


def get_regression_compare_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regression_compare.tsv"


def stooq_url(symbol: str) -> str:
    return f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
