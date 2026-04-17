from __future__ import annotations

import json
import os
from typing import cast
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
    "spy": AssetDefaults("spy", "SPY", 0.08, -0.04, 60, "drop-neutral"),
    "qqq": AssetDefaults("qqq", "QQQ", 0.08, -0.04, 60, "drop-neutral"),
    "iwm": AssetDefaults("iwm", "IWM", 0.10, -0.05, 60, "drop-neutral"),
    "dia": AssetDefaults("dia", "DIA", 0.08, -0.04, 60, "drop-neutral"),
    "mdy": AssetDefaults("mdy", "MDY", 0.10, -0.05, 60, "drop-neutral"),
    "ijh": AssetDefaults("ijh", "IJH", 0.10, -0.05, 60, "drop-neutral"),
    "ijr": AssetDefaults("ijr", "IJR", 0.10, -0.05, 60, "drop-neutral"),
    "vti": AssetDefaults("vti", "VTI", 0.08, -0.04, 60, "drop-neutral"),
    "rsp": AssetDefaults("rsp", "RSP", 0.08, -0.04, 60, "drop-neutral"),
    "vt": AssetDefaults("vt", "VT", 0.08, -0.04, 60, "drop-neutral"),
    "xlf": AssetDefaults("xlf", "XLF", 0.10, -0.05, 60, "drop-neutral"),
    "xlk": AssetDefaults("xlk", "XLK", 0.10, -0.05, 60, "drop-neutral"),
    "xle": AssetDefaults("xle", "XLE", 0.10, -0.05, 60, "drop-neutral"),
    "xli": AssetDefaults("xli", "XLI", 0.10, -0.05, 60, "drop-neutral"),
    "xlv": AssetDefaults("xlv", "XLV", 0.08, -0.04, 60, "drop-neutral"),
    "xly": AssetDefaults("xly", "XLY", 0.10, -0.05, 60, "drop-neutral"),
    "xlp": AssetDefaults("xlp", "XLP", 0.08, -0.04, 60, "drop-neutral"),
    "xlu": AssetDefaults("xlu", "XLU", 0.08, -0.04, 60, "drop-neutral"),
    "xlb": AssetDefaults("xlb", "XLB", 0.10, -0.05, 60, "drop-neutral"),
    "xlre": AssetDefaults("xlre", "XLRE", 0.08, -0.04, 60, "drop-neutral"),
    "smh": AssetDefaults("smh", "SMH", 0.12, -0.06, 60, "drop-neutral"),
    "soxx": AssetDefaults("soxx", "SOXX", 0.12, -0.06, 60, "drop-neutral"),
    "arkk": AssetDefaults("arkk", "ARKK", 0.12, -0.06, 60, "drop-neutral"),
    "kre": AssetDefaults("kre", "KRE", 0.10, -0.05, 60, "drop-neutral"),
    "xbi": AssetDefaults("xbi", "XBI", 0.12, -0.06, 60, "drop-neutral"),
    "ibb": AssetDefaults("ibb", "IBB", 0.10, -0.05, 60, "drop-neutral"),
    "itb": AssetDefaults("itb", "ITB", 0.10, -0.05, 60, "drop-neutral"),
    "xrt": AssetDefaults("xrt", "XRT", 0.10, -0.05, 60, "drop-neutral"),
    "iyt": AssetDefaults("iyt", "IYT", 0.10, -0.05, 60, "drop-neutral"),
    "tan": AssetDefaults("tan", "TAN", 0.12, -0.06, 60, "drop-neutral"),
    "gld": AssetDefaults("gld", "GLD", 0.08, -0.04, 60, "drop-neutral"),
    "slv": AssetDefaults("slv", "SLV", 0.08, -0.04, 60, "drop-neutral"),
    "uso": AssetDefaults("uso", "USO", 0.12, -0.06, 60, "drop-neutral"),
    "ung": AssetDefaults("ung", "UNG", 0.12, -0.06, 60, "drop-neutral"),
    "dba": AssetDefaults("dba", "DBA", 0.10, -0.05, 60, "drop-neutral"),
    "cper": AssetDefaults("cper", "CPER", 0.12, -0.06, 60, "drop-neutral"),
    "uup": AssetDefaults("uup", "UUP", 0.06, -0.03, 60, "drop-neutral"),
    "fxe": AssetDefaults("fxe", "FXE", 0.06, -0.03, 60, "drop-neutral"),
    "fxy": AssetDefaults("fxy", "FXY", 0.06, -0.03, 60, "drop-neutral"),
    "fxb": AssetDefaults("fxb", "FXB", 0.06, -0.03, 60, "drop-neutral"),
    "nvda": AssetDefaults("nvda", "NVDA", 0.12, -0.06, 60, "drop-neutral"),
    "tsla": AssetDefaults("tsla", "TSLA", 0.12, -0.06, 60, "drop-neutral"),
    "tlt": AssetDefaults("tlt", "TLT", 0.06, -0.03, 60, "drop-neutral"),
    "ief": AssetDefaults("ief", "IEF", 0.05, -0.025, 60, "drop-neutral"),
    "shy": AssetDefaults("shy", "SHY", 0.03, -0.015, 60, "drop-neutral"),
    "lqd": AssetDefaults("lqd", "LQD", 0.05, -0.025, 60, "drop-neutral"),
    "hyg": AssetDefaults("hyg", "HYG", 0.06, -0.03, 60, "drop-neutral"),
    "tip": AssetDefaults("tip", "TIP", 0.05, -0.025, 60, "drop-neutral"),
    "emb": AssetDefaults("emb", "EMB", 0.06, -0.03, 60, "drop-neutral"),
    "bnd": AssetDefaults("bnd", "BND", 0.04, -0.02, 60, "drop-neutral"),
    "jnk": AssetDefaults("jnk", "JNK", 0.06, -0.03, 60, "drop-neutral"),
    "mub": AssetDefaults("mub", "MUB", 0.04, -0.02, 60, "drop-neutral"),
    "eem": AssetDefaults("eem", "EEM", 0.10, -0.05, 60, "drop-neutral"),
    "efa": AssetDefaults("efa", "EFA", 0.08, -0.04, 60, "drop-neutral"),
    "ewj": AssetDefaults("ewj", "EWJ", 0.08, -0.04, 60, "drop-neutral"),
    "ewz": AssetDefaults("ewz", "EWZ", 0.12, -0.06, 60, "drop-neutral"),
    "fxi": AssetDefaults("fxi", "FXI", 0.10, -0.05, 60, "drop-neutral"),
    "kweb": AssetDefaults("kweb", "KWEB", 0.12, -0.06, 60, "drop-neutral"),
    "inda": AssetDefaults("inda", "INDA", 0.10, -0.05, 60, "drop-neutral"),
    "rsx": AssetDefaults("rsx", "RSX", 0.12, -0.06, 60, "drop-neutral"),
    "arkf": AssetDefaults("arkf", "ARKF", 0.12, -0.06, 60, "drop-neutral"),
    "arkg": AssetDefaults("arkg", "ARKG", 0.12, -0.06, 60, "drop-neutral"),
    "aapl": AssetDefaults("aapl", "AAPL", 0.10, -0.05, 60, "drop-neutral"),
    "msft": AssetDefaults("msft", "MSFT", 0.10, -0.05, 60, "drop-neutral"),
    "amzn": AssetDefaults("amzn", "AMZN", 0.12, -0.06, 60, "drop-neutral"),
    "googl": AssetDefaults("googl", "GOOGL", 0.10, -0.05, 60, "drop-neutral"),
    "meta": AssetDefaults("meta", "META", 0.12, -0.06, 60, "drop-neutral"),
    "mu": AssetDefaults("mu", "MU", 0.12, -0.06, 60, "drop-neutral"),
    "amd": AssetDefaults("amd", "AMD", 0.12, -0.06, 60, "drop-neutral"),
    "nflx": AssetDefaults("nflx", "NFLX", 0.12, -0.06, 60, "drop-neutral"),
    "avgo": AssetDefaults("avgo", "AVGO", 0.12, -0.06, 60, "drop-neutral"),
    "jpm": AssetDefaults("jpm", "JPM", 0.10, -0.05, 60, "drop-neutral"),
    "gs": AssetDefaults("gs", "GS", 0.10, -0.05, 60, "drop-neutral"),
    "bac": AssetDefaults("bac", "BAC", 0.10, -0.05, 60, "drop-neutral"),
    "v": AssetDefaults("v", "V", 0.08, -0.04, 60, "drop-neutral"),
    "ma": AssetDefaults("ma", "MA", 0.08, -0.04, 60, "drop-neutral"),
    "unh": AssetDefaults("unh", "UNH", 0.08, -0.04, 60, "drop-neutral"),
    "lly": AssetDefaults("lly", "LLY", 0.10, -0.05, 60, "drop-neutral"),
    "jnj": AssetDefaults("jnj", "JNJ", 0.08, -0.04, 60, "drop-neutral"),
    "xom": AssetDefaults("xom", "XOM", 0.10, -0.05, 60, "drop-neutral"),
    "cvx": AssetDefaults("cvx", "CVX", 0.10, -0.05, 60, "drop-neutral"),
    "ko": AssetDefaults("ko", "KO", 0.08, -0.04, 60, "drop-neutral"),
    "pep": AssetDefaults("pep", "PEP", 0.08, -0.04, 60, "drop-neutral"),
    "cost": AssetDefaults("cost", "COST", 0.08, -0.04, 60, "drop-neutral"),
    "wmt": AssetDefaults("wmt", "WMT", 0.08, -0.04, 60, "drop-neutral"),
    "hd": AssetDefaults("hd", "HD", 0.10, -0.05, 60, "drop-neutral"),
    "cat": AssetDefaults("cat", "CAT", 0.10, -0.05, 60, "drop-neutral"),
    "ba": AssetDefaults("ba", "BA", 0.12, -0.06, 60, "drop-neutral"),
    "ge": AssetDefaults("ge", "GE", 0.10, -0.05, 60, "drop-neutral"),
    "crm": AssetDefaults("crm", "CRM", 0.10, -0.05, 60, "drop-neutral"),
    "adbe": AssetDefaults("adbe", "ADBE", 0.10, -0.05, 60, "drop-neutral"),
    "btc_usd": AssetDefaults("btc_usd", "BTC-USD", 0.20, -0.10, 60, "drop-neutral"),
    "eth_usd": AssetDefaults("eth_usd", "ETH-USD", 0.22, -0.11, 60, "drop-neutral"),
    "mstr": AssetDefaults("mstr", "MSTR", 0.20, -0.10, 60, "drop-neutral"),
    "coin": AssetDefaults("coin", "COIN", 0.18, -0.09, 60, "drop-neutral"),
    "riot": AssetDefaults("riot", "RIOT", 0.20, -0.10, 60, "drop-neutral"),
    "mara": AssetDefaults("mara", "MARA", 0.20, -0.10, 60, "drop-neutral"),
    "bito": AssetDefaults("bito", "BITO", 0.18, -0.09, 60, "drop-neutral"),
    "ethe": AssetDefaults("ethe", "ETHE", 0.20, -0.10, 60, "drop-neutral"),
    "ibit": AssetDefaults("ibit", "IBIT", 0.18, -0.09, 60, "drop-neutral"),
    "bitb": AssetDefaults("bitb", "BITB", 0.18, -0.09, 60, "drop-neutral"),
}
REGRESSION_ASSET_KEYS = {"qqq", "tlt", "xle"}
MONITOR_BOARD_ASSET_KEYS = ("gld", "slv", "iwm", "spy", "nvda", "tsla")
MONITOR_PRIORITY_RESEARCH_ASSET_KEYS = ("xlp", "ijh", "fxb", "smh", "pep", "vt", "rsp", "meta")

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


def get_live_extra_features(asset_key: str | None = None) -> tuple[str, ...]:
    config = load_asset_config(asset_key)
    raw = config.get("live_extra_features", [])
    if isinstance(raw, str):
        return tuple(part.strip() for part in raw.split(",") if part.strip())
    if isinstance(raw, list):
        return tuple(str(part).strip() for part in raw if str(part).strip())
    return ()


def get_live_model_family(asset_key: str | None = None) -> str:
    config = load_asset_config(asset_key)
    value = str(config.get("live_model_family", "logistic")).strip().lower()
    return value if value else "logistic"


def get_live_execution_rule(asset_key: str | None = None) -> str:
    config = load_asset_config(asset_key)
    value = str(config.get("live_execution_rule", "threshold")).strip().lower()
    return value if value else "threshold"


def get_live_operator_line_id(asset_key: str | None = None) -> str:
    config = load_asset_config(asset_key)
    return str(config.get("live_operator_line_id", "")).strip()


def get_live_term_panic_settings(asset_key: str | None = None) -> dict[str, object]:
    config = load_asset_config(asset_key)
    feature = str(config.get("live_term_panic_feature", "")).strip()
    threshold_raw = config.get("live_term_panic_threshold")
    threshold = float(cast(float | int | str, threshold_raw)) if threshold_raw is not None else None
    return {
        "feature": feature,
        "threshold": threshold,
    }


def get_live_mixed_signature(asset_key: str | None = None) -> dict[str, object]:
    config = load_asset_config(asset_key)
    return {
        "left_expert": str(config.get("live_left_expert", "")).strip(),
        "right_expert": str(config.get("live_right_expert", "")).strip(),
        "outer_gate_feature": str(config.get("live_outer_gate_feature", "")).strip(),
        "outer_gate_threshold": float(cast(float | int | str, config.get("live_outer_gate_threshold", 0.0))),
    }


def get_live_xgboost_params(asset_key: str | None = None) -> dict[str, int | float]:
    config = load_asset_config(asset_key)
    raw = config.get("live_xgboost_params", {})
    if not isinstance(raw, dict):
        return {}

    params: dict[str, int | float] = {}
    if "n_estimators" in raw:
        params["n_estimators"] = int(raw["n_estimators"])
    if "max_depth" in raw:
        params["max_depth"] = int(raw["max_depth"])
    if "learning_rate" in raw:
        params["learning_rate"] = float(raw["learning_rate"])
    return params


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


def get_latest_prediction_path(asset_key: str | None = None) -> Path:
    return get_cache_dir(asset_key) / "latest_prediction.json"


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


def get_regression_recent_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regression_recent.tsv"


def get_regression_recent_chart_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regression_recent.html"


def uses_regression_chart(asset_key: str | None = None) -> bool:
    key = asset_key or get_asset_key()
    return key in REGRESSION_ASSET_KEYS


def get_primary_chart_path(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    if uses_regression_chart(key):
        return get_regression_recent_chart_path(key)
    return get_chart_output_path(key)


def get_monitor_card_chart_path(asset_key: str | None = None) -> Path:
    key = asset_key or get_asset_key()
    regression_path = get_regression_recent_chart_path(key)
    if uses_regression_chart(key) and regression_path.exists():
        return regression_path
    signal_path = get_chart_output_path(key)
    if signal_path.exists():
        return signal_path
    if regression_path.exists():
        return regression_path
    active_status_path = get_active_status_chart_path(key)
    if active_status_path.exists():
        return active_status_path
    return get_primary_chart_path(key)


def get_regression_walkforward_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "regression_walkforward.tsv"


def get_active_status_output_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "active_status_summary.tsv"


def get_active_status_chart_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "active_status.html"


def get_monitor_snapshot_path(asset_key: str | None = None) -> Path:
    return get_asset_dir(asset_key) / "monitor_snapshot.tsv"


def get_monitor_board_path() -> Path:
    return REPO_DIR / "monitor_board.tsv"


def get_monitor_board_chart_path() -> Path:
    return REPO_DIR / "monitor_board.html"


def get_monitor_priority_path() -> Path:
    return REPO_DIR / "monitor_priority.tsv"


def get_monitor_priority_chart_path() -> Path:
    return REPO_DIR / "monitor_priority.html"


def get_monitor_focus_path() -> Path:
    return REPO_DIR / "monitor_focus.tsv"


def get_monitor_focus_chart_path() -> Path:
    return REPO_DIR / "monitor_focus.html"


def stooq_url(symbol: str) -> str:
    return f"https://stooq.com/q/d/l/?s={symbol.lower()}.us&i=d"
