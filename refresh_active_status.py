from __future__ import annotations

import json
from pathlib import Path
from typing import cast

import pandas as pd

import asset_config as ac
import chart_signals as cs


def read_tsv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t")


def latest_row(frame: pd.DataFrame) -> pd.Series:
    if frame.empty:
        raise ValueError("Expected non-empty frame")
    return frame.iloc[-1]


def fmt_date(value: object) -> str:
    if value is None:
        return ""
    text = str(value)
    return text[:10] if text else ""


def read_signal_rows_from_cache(cache_dir: Path, asset_key: str, lookback_days: int = 60) -> pd.DataFrame:
    path = cache_dir / "signal_rows.tsv"
    if not path.exists():
        raise FileNotFoundError(f"Missing signal rows cache for {asset_key}: {path}")
    frame = read_tsv(path)
    if frame.empty:
        raise ValueError(f"Signal rows cache is empty for {asset_key}: {path}")
    return frame.tail(lookback_days).reset_index(drop=True)


def _normalize_feature_names(raw: object) -> tuple[str, ...]:
    values: list[str] = []
    if isinstance(raw, str):
        values = [part.strip() for part in raw.split(",") if part.strip()]
    elif isinstance(raw, (list, tuple, set)):
        values = [str(part).strip() for part in raw if str(part).strip()]
    return tuple(sorted(dict.fromkeys(values)))


def _normalize_xgboost_params(raw: object) -> dict[str, int | float]:
    if not isinstance(raw, dict):
        return {}

    normalized: dict[str, int | float] = {}
    if "n_estimators" in raw:
        normalized["n_estimators"] = int(cast(int | float | str, raw["n_estimators"]))
    if "max_depth" in raw:
        normalized["max_depth"] = int(cast(int | float | str, raw["max_depth"]))
    if "learning_rate" in raw:
        normalized["learning_rate"] = float(cast(int | float | str, raw["learning_rate"]))
    return normalized


def _payload_raw_model_signal(payload: dict[str, object]) -> str:
    signal_summary = cast(dict[str, object], payload.get("signal_summary", {}))
    explicit_signal = str(signal_summary.get("raw_model_signal", "")).strip()
    if explicit_signal:
        return explicit_signal
    model_signal_summary = cast(dict[str, object], payload.get("model_signal_summary", {}))
    return str(model_signal_summary.get("signal", "")).strip()


def _rounded_or_none(value: object, digits: int) -> float | None:
    if value is None:
        return None
    is_missing = pd.isna(value)
    if isinstance(is_missing, bool) and is_missing:
        return None
    return round(float(cast(float | int | str, value)), digits)


def _is_missing_scalar(value: object) -> bool:
    is_missing = pd.isna(value)
    return bool(is_missing) if isinstance(is_missing, bool) else False


def _float_or_none(value: object) -> float | None:
    if value is None or _is_missing_scalar(value):
        return None
    try:
        return float(cast(float | int | str, value))
    except (TypeError, ValueError):
        return None


def _latest_signal_numeric_digits(field_name: str) -> int:
    return 2 if field_name in {"close", "rsi_14"} else 4


def validate_latest_signal_cache(payload: dict[str, object], signal_rows: pd.DataFrame, asset_key: str) -> None:
    latest_signal_row = latest_row(signal_rows)
    mismatches: list[str] = []

    authoritative_row = cs.build_authoritative_latest_signal_row(latest_signal_row.to_dict(), payload)
    authoritative_fields = [
        "date",
        "close",
        "signal",
        "raw_model_signal",
        "buy_point_ok",
        "buy_point_warnings",
        "probability",
        "threshold",
        "confidence_gap",
        "rule_selected",
        "rule_cutoff",
        "rule_name",
        "percentile_rank",
        "model_rationale",
        "rule_rationale",
        "ret_20",
        "ret_60",
        "drawdown_20",
        "sma_gap_20",
        "sma_gap_60",
        "volume_vs_20",
        "rsi_14",
    ]

    for field_name in authoritative_fields:
        expected = authoritative_row.get(field_name)
        actual = latest_signal_row.get(field_name)
        expected_missing = expected is None or _is_missing_scalar(expected)
        actual_missing = _is_missing_scalar(actual)
        if expected_missing and actual_missing:
            continue
        if field_name == "buy_point_ok" or field_name == "rule_selected":
            if bool(actual) != bool(expected):
                mismatches.append(f"{field_name} row={bool(actual)} payload={bool(expected)}")
            continue
        if field_name in {
            "close",
            "probability",
            "threshold",
            "confidence_gap",
            "rule_cutoff",
            "percentile_rank",
            "ret_20",
            "ret_60",
            "drawdown_20",
            "sma_gap_20",
            "sma_gap_60",
            "volume_vs_20",
            "rsi_14",
        }:
            digits = _latest_signal_numeric_digits(field_name)
            if _rounded_or_none(actual, digits) != _rounded_or_none(expected, digits):
                mismatches.append(f"{field_name} row={actual} payload={expected}")
            continue
        actual_text = fmt_date(actual) if field_name == "date" else str(actual).strip()
        expected_text = fmt_date(expected) if field_name == "date" else str(expected).strip()
        if actual_text != expected_text:
            mismatches.append(f"{field_name} row={actual_text} payload={expected_text}")

    if mismatches:
        raise ValueError(f"Latest signal cache drift detected for {asset_key}: {'; '.join(mismatches)}")


def build_iwm(asset_dir: Path) -> pd.DataFrame:
    usage = read_tsv(asset_dir / "operator_usage_summary.tsv")
    rows: list[dict[str, object]] = []
    notes = {
        "baseline_threshold": "Default operating line. Use this for actual IWM watchlist decisions.",
        "rs_sidecar_threshold": "Context-only sidecar. Treat as IWM-vs-SPY confirmation rather than a separate signal stream.",
    }
    for _, row in usage.iterrows():
        rows.append(
            {
                "line_id": row["model_name"],
                "lane_type": "binary_operator",
                "role": "primary" if row["model_name"] == "baseline_threshold" else "sidecar",
                "preferred": row["model_name"] == "baseline_threshold",
                "status": "active" if bool(row["latest_selected"]) else "inactive",
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": fmt_date(row["latest_date"]),
                "latest_value": float(row["latest_score"]),
                "latest_selected": bool(row["latest_selected"]),
                "cutoff": float(row["cutoff"]),
                "last_selected_date": fmt_date(row["last_selected_date"]),
                "usage_note": notes[str(row["model_name"])],
            }
        )
    return pd.DataFrame(rows)


def build_spy(asset_dir: Path) -> pd.DataFrame:
    usage = read_tsv(asset_dir / "operator_usage_summary.tsv")
    rows: list[dict[str, object]] = []
    for _, row in usage.iterrows():
        rows.append(
            {
                "line_id": row["model_name"],
                "lane_type": "binary_operator",
                "role": "reference_side_line",
                "preferred": row["model_name"] == "baseline_top10",
                "status": "inactive",
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": fmt_date(row["latest_date"]),
                "latest_value": float(row["latest_score"]),
                "latest_selected": bool(row["latest_selected"]),
                "cutoff": float(row["cutoff"]),
                "last_selected_date": fmt_date(row["last_selected_date"]),
                "usage_note": "Reference-only. Keep for market context, not for live entries.",
            }
        )
    return pd.DataFrame(rows)


def build_tlt(asset_dir: Path) -> pd.DataFrame:
    recent = read_tsv(asset_dir / "regression_recent.tsv")
    latest = latest_row(recent)
    latest_selected = bool(latest["selected"])
    selected_mask = recent["selected"].fillna(False).astype(bool)
    return pd.DataFrame(
        [
            {
                "line_id": "atr_pct_20_bottom5",
                "lane_type": "regression_watchlist",
                "role": "research_primary",
                "preferred": True,
                "status": "inactive" if not latest_selected else "active",
                "recent_selected_count": int(recent["selected"].sum()),
                "latest_date": fmt_date(latest["date"]),
                "latest_value": float(latest["predicted_return"]),
                "latest_selected": latest_selected,
                "cutoff": float(latest["bucket_cutoff"]),
                "last_selected_date": fmt_date(recent.loc[selected_mask, "date"].max()) if bool(selected_mask.any()) else "",
                "usage_note": "Research-only volatility-style ranking line. Do not treat as a live operator yet.",
            }
        ]
    )


def build_xle(asset_dir: Path) -> pd.DataFrame:
    pref = read_tsv(asset_dir / "regression_operating_preference.tsv")
    recent = read_tsv(asset_dir / "regression_recent.tsv")
    latest = latest_row(recent)
    rows: list[dict[str, object]] = []
    for _, row in pref.iterrows():
        rows.append(
            {
                "line_id": row["model_name"],
                "lane_type": "regression_watchlist",
                "role": "primary" if row["model_name"] == "distance_to_252_high" else "sidecar",
                "preferred": row["model_name"] == "distance_to_252_high",
                "status": "watchlist_ready" if row["model_name"] == "distance_to_252_high" else "secondary",
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": fmt_date(latest["date"]) if row["model_name"] == "distance_to_252_high" else "",
                "latest_value": float(latest["predicted_return"]) if row["model_name"] == "distance_to_252_high" else None,
                "latest_selected": bool(latest["selected"]) if row["model_name"] == "distance_to_252_high" else False,
                "cutoff": float(row["cutoff"]),
                "last_selected_date": fmt_date(row["last_selected_date"]),
                "usage_note": "Use the distance-based bottom-10% line as the active XLE watchlist." if row["model_name"] == "distance_to_252_high" else "Keep only as a static-split side study.",
            }
        )
    return pd.DataFrame(rows)


def build_nvda(asset_dir: Path) -> pd.DataFrame:
    preferred_line = str(
        ac.load_asset_config("nvda").get("live_operator_line_id", "ret_60_sma_gap_60_atr_pct_20")
    ).strip() or "ret_60_sma_gap_60_atr_pct_20"
    pref = read_tsv(asset_dir / "operator_preference_summary.tsv")
    usage = read_tsv(asset_dir / "operator_usage_summary.tsv")
    usage_map = {str(row["model_name"]): row for _, row in usage.iterrows()}
    rows: list[dict[str, object]] = []
    for _, row in pref.iterrows():
        key = str(row["model_name"])
        usage_row = usage_map[key]
        rows.append(
            {
                "line_id": key,
                "lane_type": "binary_watchlist",
                "role": "primary" if key == preferred_line else "sidecar",
                "preferred": key == preferred_line,
                "status": "watchlist_ready" if key == preferred_line else "secondary",
                "recent_selected_count": int(usage_row["recent_selected_count"]),
                "latest_date": fmt_date(usage_row["latest_date"]),
                "latest_value": float(usage_row["latest_score"]),
                "latest_selected": bool(usage_row["latest_selected"]),
                "cutoff": float(usage_row["cutoff"]) if usage_row is not None else float(row["cutoff"]),
                "last_selected_date": fmt_date(usage_row["last_selected_date"]),
                "usage_note": "Best current NVDA watchlist candidate. Keep this return-gap line as the default lane." if key == preferred_line else "Secondary NVDA watchlist candidate; keep for comparison rather than the default lane.",
            }
        )
    latest_prediction_path = ac.get_latest_prediction_path("nvda")
    if latest_prediction_path.exists():
        payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
        if not nvda_live_cache_matches_preferred_line(payload, preferred_line):
            raise ValueError(f"NVDA preferred line '{preferred_line}' cannot be validated from live cache provenance.")
        preferred_live_row = build_nvda_preferred_live_row(preferred_line, payload, latest_prediction_path.parent)
        rows = [row for row in rows if not bool(row["preferred"])]
        rows.insert(0, preferred_live_row)
    elif not any(bool(row["preferred"]) for row in rows):
        latest_prediction_path = ac.get_latest_prediction_path("nvda")
        raise FileNotFoundError(f"Missing NVDA latest prediction file: {latest_prediction_path}")
    return pd.DataFrame(rows)


def build_nvda_preferred_live_row(preferred_line: str, payload: dict[str, object], cache_dir: Path) -> dict[str, object]:
    signal_rows = read_signal_rows_from_cache(cache_dir, "nvda", 60)
    validate_latest_signal_cache(payload, signal_rows, "nvda")
    selected_rows = signal_rows.loc[signal_rows["signal"].astype(str) != "no_entry"]
    signal_summary = cast(dict[str, object], payload["signal_summary"])
    latest_signal = str(signal_summary["signal"])
    return {
        "line_id": preferred_line,
        "lane_type": "binary_watchlist",
        "role": "primary",
        "preferred": True,
        "status": "watchlist_ready",
        "recent_selected_count": int(len(selected_rows)),
        "latest_date": str(payload["latest_raw_date"]),
        "latest_value": float(cast(float | int | str, signal_summary["predicted_probability"])),
        "latest_selected": latest_signal != "no_entry",
        "cutoff": float(cast(float | int | str, signal_summary["decision_threshold"])),
        "last_selected_date": fmt_date(selected_rows.iloc[-1]["date"]) if not selected_rows.empty else "",
        "usage_note": "Best current NVDA watchlist candidate. Keep this return-gap line as the default lane.",
    }


def build_mu(asset_dir: Path) -> pd.DataFrame:
    config = ac.load_asset_config("mu")
    preferred_line = str(config.get("live_operator_line_id", "")).strip() or "mu_tb30_ret_60_vol_ratio_20_120_top12_5"
    latest_prediction_path = ac.get_latest_prediction_path("mu")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing MU latest prediction file: {latest_prediction_path}")

    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    signal_rows = read_signal_rows_from_cache(latest_prediction_path.parent, "mu", 60)
    validate_latest_signal_cache(payload, signal_rows, "mu")
    execution_selected_rows = signal_rows.loc[signal_rows["signal"].astype(str) != "no_entry"]
    model_selected_rows = signal_rows.loc[signal_rows["raw_model_signal"].astype(str) != "no_entry"]
    signal_summary = cast(dict[str, object], payload["signal_summary"])
    model_signal_summary = cast(dict[str, object], payload["model_signal_summary"])
    execution_rule = str(signal_summary.get("execution_rule", "threshold")).strip() or "threshold"

    return pd.DataFrame(
        [
            {
                "line_id": preferred_line,
                "lane_type": "binary_live_model",
                "role": "execution_preference",
                "preferred": True,
                "status": "watchlist_ready" if str(signal_summary.get("signal", "no_entry")) != "no_entry" else "inactive",
                "recent_selected_count": int(len(execution_selected_rows)),
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(cast(float | int | str, signal_summary["predicted_probability"])),
                "latest_selected": str(signal_summary.get("signal", "no_entry")) != "no_entry",
                "cutoff": float(cast(float | int | str, signal_summary["decision_threshold"])),
                "last_selected_date": fmt_date(execution_selected_rows.iloc[-1]["date"]) if not execution_selected_rows.empty else "",
                "usage_note": f"Preferred MU execution line uses the tb30 ret_60 plus vol_ratio_20_120 live model with the `{execution_rule}` overlay.",
            },
            {
                "line_id": "mu_tb30_ret_60_vol_ratio_20_120_model_reference",
                "lane_type": "binary_live_model",
                "role": "model_reference",
                "preferred": False,
                "status": "secondary",
                "recent_selected_count": int(len(model_selected_rows)),
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(cast(float | int | str, model_signal_summary["predicted_probability"])),
                "latest_selected": str(model_signal_summary.get("signal", "no_entry")) != "no_entry",
                "cutoff": float(cast(float | int | str, model_signal_summary["decision_threshold"])),
                "last_selected_date": fmt_date(model_selected_rows.iloc[-1]["date"]) if not model_selected_rows.empty else "",
                "usage_note": "Balance-first MU model reference stays on tb30 with ret_60 plus vol_ratio_20_120; keep this as context while the stricter execution overlay decides entries.",
            },
            {
                "line_id": "mu_tb20_ret_60_vol_ratio_20_120_overlay_research",
                "lane_type": "binary_operator",
                "role": "research_side_line",
                "preferred": False,
                "status": "secondary",
                "recent_selected_count": 0,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": None,
                "latest_selected": False,
                "cutoff": None,
                "last_selected_date": "",
                "usage_note": "Research-only MU sidecar: tb20 plus vol_ratio_20_120 with top 11.5% is now the lead challenger execution overlay, but it is not the default live scorer yet.",
            },
        ]
    )


def nvda_live_cache_matches_preferred_line(payload: dict[str, object], preferred_line: str) -> bool:
    explicit_line = str(payload.get("live_operator_line_id", "")).strip()
    if explicit_line:
        return explicit_line == preferred_line

    expected_feature_map = {
        "ret_60_sma_gap_60_atr_pct_20": {"ret_60", "sma_gap_60", "atr_pct_20"},
    }
    expected_features = expected_feature_map.get(preferred_line)
    if expected_features is None:
        return False

    top_level_features = payload.get("model_extra_features", [])
    if not isinstance(top_level_features, list):
        top_level_features = []
    model_summary = cast(dict[str, object], payload.get("model_summary", {}))
    summary_features = model_summary.get("model_extra_features", [])
    if not isinstance(summary_features, list):
        summary_features = []

    payload_features = {
        str(feature).strip()
        for feature in [*top_level_features, *summary_features]
        if str(feature).strip()
    }
    return payload_features == expected_features


def get_tsla_live_preferences() -> dict[str, object]:
    config = ac.load_asset_config("tsla")
    reference_top_pct = int(cast(int | float | str, config.get("live_reference_top_pct", 30)))
    return {
        "preferred_line": "xgboost_tb30_distance_live",
        "model_family": str(config.get("live_model_family", config.get("model_family", "logistic"))).strip(),
        "label_mode": str(config.get("live_label_mode", config.get("label_mode", ""))).strip(),
        "reference_rule": f"top_{reference_top_pct}pct",
        "extra_features": _normalize_feature_names(config.get("live_extra_features", [])),
        "xgboost_params": _normalize_xgboost_params(config.get("live_xgboost_params", {})),
    }


def tsla_live_cache_matches_preferred_line(payload: dict[str, object], tsla_preferences: dict[str, object]) -> bool:
    model_summary = cast(dict[str, object], payload.get("model_summary", {}))
    model_family = str(model_summary.get("model_family", "")).strip()
    label_mode = str(model_summary.get("label_mode", "")).strip()
    if model_family != str(tsla_preferences["model_family"]) or label_mode != str(tsla_preferences["label_mode"]):
        return False

    explicit_line = str(payload.get("live_operator_line_id", "")).strip()
    if not explicit_line:
        return False
    if explicit_line != str(tsla_preferences["preferred_line"]):
        return False

    reference_rule = str(model_summary.get("reference_percentile_rule", "")).strip()
    if reference_rule != str(tsla_preferences["reference_rule"]):
        return False

    payload_feature_names = list(cast(tuple[str, ...], _normalize_feature_names(payload.get("model_extra_features", []))))
    payload_feature_names.extend(_normalize_feature_names(model_summary.get("model_extra_features", [])))
    payload_features = _normalize_feature_names(payload_feature_names)
    if payload_features != cast(tuple[str, ...], tsla_preferences["extra_features"]):
        return False

    payload_xgboost_params = _normalize_xgboost_params(model_summary.get("xgboost_params", {}))
    return payload_xgboost_params == cast(dict[str, int | float], tsla_preferences["xgboost_params"])


def get_slv_live_preferences() -> dict[str, str]:
    config = ac.load_asset_config("slv")
    preferred_line = str(config.get("live_operator_line_id", "")).strip()
    model_family = str(config.get("live_model_family", "")).strip()
    label_mode = str(config.get("live_label_mode", config.get("label_mode", ""))).strip()
    benchmark_symbol = str(config.get("benchmark_symbol", "")).strip().upper()
    return {
        "preferred_line": preferred_line,
        "model_family": model_family,
        "label_mode": label_mode,
        "benchmark_symbol": benchmark_symbol,
    }


def normalize_slv_live_preferences(slv_preferences: dict[str, str]) -> dict[str, str]:
    preferred_line = str(
        slv_preferences.get("preferred_line", slv_preferences.get("live_operator_line_id", ""))
    ).strip()
    model_family = str(slv_preferences.get("model_family", slv_preferences.get("live_model_family", ""))).strip()
    label_mode = str(slv_preferences.get("label_mode", slv_preferences.get("live_label_mode", ""))).strip()
    benchmark_symbol = str(slv_preferences.get("benchmark_symbol", "")).strip().upper()
    return {
        "preferred_line": preferred_line,
        "model_family": model_family,
        "label_mode": label_mode,
        "benchmark_symbol": benchmark_symbol,
    }


def slv_live_cache_matches_preferred_line(payload: dict[str, object], slv_preferences: dict[str, str]) -> bool:
    normalized_preferences = normalize_slv_live_preferences(slv_preferences)
    preferred_line = normalized_preferences["preferred_line"]
    model_summary = cast(dict[str, object], payload.get("model_summary", {}))
    model_family = str(model_summary.get("model_family", "")).strip()
    label_mode = str(model_summary.get("label_mode", "")).strip()
    if model_family != normalized_preferences["model_family"] or label_mode != normalized_preferences["label_mode"]:
        return False

    explicit_line = str(payload.get("live_operator_line_id", "")).strip()
    if explicit_line != preferred_line:
        return False

    live_provenance = cast(dict[str, object], payload.get("live_provenance", {}))
    provenance_line = str(live_provenance.get("operator_line_id", "")).strip()
    provenance_benchmark = str(live_provenance.get("benchmark_symbol", "")).strip().upper()
    outer_gate_feature = str(live_provenance.get("outer_gate_feature", "")).strip()
    return (
        provenance_line == preferred_line
        and provenance_benchmark == normalized_preferences["benchmark_symbol"]
        and "benchmark" in outer_gate_feature
    )


def build_qqq(asset_dir: Path) -> pd.DataFrame:
    pref = read_tsv(asset_dir / "operating_preference_summary.tsv")
    recent = read_tsv(asset_dir / "regression_recent.tsv")
    latest = latest_row(recent)
    rows: list[dict[str, object]] = []
    for _, row in pref.iterrows():
        key = str(row["model_name"])
        rows.append(
            {
                "line_id": key,
                "lane_type": "regression_watchlist",
                "role": "primary" if key == "distance_bottom5" else "sidecar",
                "preferred": key == "distance_bottom5",
                "status": "watchlist_ready" if key == "distance_bottom5" else "secondary",
                "recent_selected_count": int(row["recent_selected_count"]),
                "latest_date": fmt_date(latest["date"]) if key == "distance_bottom5" else "",
                "latest_value": float(latest["predicted_return"]) if key == "distance_bottom5" else None,
                "latest_selected": bool(latest["selected"]) if key == "distance_bottom5" else False,
                "cutoff": float(row["cutoff"]),
                "last_selected_date": fmt_date(row["last_selected_date"]),
                "usage_note": "Default QQQ watchlist. Robustest sparse-bottom candidate." if key == "distance_bottom5" else "Side study only; keep for research context, not as the default line.",
            }
        )
    return pd.DataFrame(rows)


def build_tsla(asset_dir: Path) -> pd.DataFrame:
    if ac.get_live_model_family("tsla") == "xgboost":
        tsla_preferences = get_tsla_live_preferences()
        latest_prediction_path = ac.get_latest_prediction_path("tsla")
        if not latest_prediction_path.exists():
            raise FileNotFoundError(f"Missing TSLA latest prediction file: {latest_prediction_path}")
        payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
        preferred_line = str(tsla_preferences["preferred_line"])
        if not tsla_live_cache_matches_preferred_line(payload, tsla_preferences):
            raise ValueError(f"TSLA preferred line '{preferred_line}' cannot be validated from live cache provenance.")
        signal_rows = read_signal_rows_from_cache(latest_prediction_path.parent, "tsla", 60)
        validate_latest_signal_cache(payload, signal_rows, "tsla")
        selected_rows = signal_rows.loc[signal_rows["signal"].astype(str) != "no_entry"]
        recent_selected_count = int(len(selected_rows))
        latest_signal = str(payload["signal_summary"]["signal"])
        last_selected_date = ""
        if not selected_rows.empty:
            last_selected_date = fmt_date(selected_rows.iloc[-1]["date"])
        return pd.DataFrame(
            [
                {
                    "line_id": preferred_line,
                    "lane_type": "binary_live_model",
                    "role": "execution_preference",
                    "preferred": True,
                    "status": "active" if latest_signal != "no_entry" else "inactive",
                    "recent_selected_count": recent_selected_count,
                    "latest_date": str(payload["latest_raw_date"]),
                    "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                    "latest_selected": latest_signal != "no_entry",
                    "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                    "last_selected_date": last_selected_date,
                    "usage_note": "Primary TSLA live line stays on the adopted tuned XGBoost TB30 distance_to_252_high strategy.",
                }
            ]
        )

    pref = read_tsv(asset_dir / "operator_preference_summary.tsv")
    usage = read_tsv(asset_dir / "operator_usage_summary.tsv")
    usage_map = {str(row["model_name"]): row for _, row in usage.iterrows()}
    rows: list[dict[str, object]] = []
    for _, row in pref.iterrows():
        key = str(row["model_name"])
        usage_row = usage_map.get(key)
        rows.append(
            {
                "line_id": key,
                "lane_type": "binary_operator",
                "role": "execution_preference" if key == "fallback_top15" else "model_overlay",
                "preferred": key == "fallback_top15",
                "status": "preferred_overlay" if key == "fallback_top15" else "secondary",
                "recent_selected_count": int(usage_row["recent_selected_count"]) if usage_row is not None else int(row["recent_selected_count"]),
                "latest_date": fmt_date(usage_row["latest_date"]) if usage_row is not None else "",
                "latest_value": float(usage_row["latest_score"]) if usage_row is not None else None,
                "latest_selected": bool(usage_row["latest_selected"]) if usage_row is not None else False,
                "cutoff": float(usage_row["cutoff"]) if usage_row is not None else float(row["cutoff"]),
                "last_selected_date": fmt_date(usage_row["last_selected_date"]) if usage_row is not None else fmt_date(row["last_selected_date"]),
                "usage_note": "Preferred conservative execution overlay for TSLA." if key == "fallback_top15" else "Keep as model-reference overlay, not the main execution rule.",
            }
        )
    return pd.DataFrame(rows)


BUILDERS = {
    "gld": None,
    "iwm": build_iwm,
    "mu": build_mu,
    "slv": None,
    "spy": build_spy,
    "tlt": build_tlt,
    "xle": build_xle,
    "nvda": build_nvda,
    "qqq": build_qqq,
    "tsla": build_tsla,
}


def build_followup_round2_status(asset_dir: Path) -> pd.DataFrame:
    decision_path = asset_dir / "followup_round2_decision_summary.tsv"
    operator_path = asset_dir / "followup_round2_operator_summary.tsv"
    if not decision_path.exists() or not operator_path.exists():
        raise FileNotFoundError(f"Missing round-2 follow-up files for {asset_dir.name}")
    decision = read_tsv(decision_path)
    operator = read_tsv(operator_path)
    rows: list[dict[str, object]] = []
    for idx, row in decision.iterrows():
        matches = operator.loc[
            (operator["model_name"] == row["model_name"]) & (operator["best_rule_name"] == row["best_rule_name"])
        ]
        op_row = matches.iloc[0] if not matches.empty else operator.loc[operator["model_name"] == row["model_name"]].iloc[0]
        rows.append(
            {
                "line_id": f'{row["model_name"]}::{row["best_rule_name"]}',
                "lane_type": "deep_research",
                "role": "primary" if idx == 0 else "research_side_line",
                "preferred": idx == 0,
                "status": "watchlist_ready" if int(op_row["recent_selected_count"]) > 0 else "inactive",
                "recent_selected_count": int(op_row["recent_selected_count"]),
                "latest_date": fmt_date(op_row["latest_date"]),
                "latest_value": float(op_row["latest_score"]),
                "latest_selected": bool(op_row["latest_selected"]),
                "cutoff": float(op_row["cutoff"]),
                "last_selected_date": fmt_date(op_row["last_selected_date"]),
                "usage_note": (
                    f'Second-round deep-research line with round2_score={float(row["round2_score"]):.4f}; '
                    f'best rule avg_return={float(row["best_rule_avg_return"]):.4f} across {int(row["best_rule_trade_count"])} trades.'
                ),
            }
        )
    return pd.DataFrame(rows)


def build_followup_round3_status(asset_dir: Path) -> pd.DataFrame:
    decision_path = asset_dir / "followup_round3_decision_summary.tsv"
    operator_path = asset_dir / "followup_round3_operator_summary.tsv"
    if not decision_path.exists() or not operator_path.exists():
        raise FileNotFoundError(f"Missing round-3 follow-up files for {asset_dir.name}")
    decision = read_tsv(decision_path)
    operator = read_tsv(operator_path)
    rows: list[dict[str, object]] = []
    for idx, row in decision.iterrows():
        matches = operator.loc[
            (operator["model_name"] == row["model_name"]) & (operator["best_rule_name"] == row["best_rule_name"])
        ]
        op_row = matches.iloc[0] if not matches.empty else operator.loc[operator["model_name"] == row["model_name"]].iloc[0]
        rows.append(
            {
                "line_id": f'{row["model_name"]}::{row["best_rule_name"]}',
                "lane_type": "deep_research_round3",
                "role": "primary" if idx == 0 else "research_side_line",
                "preferred": idx == 0,
                "status": "watchlist_ready" if int(op_row["recent_selected_count"]) > 0 else "inactive",
                "recent_selected_count": int(op_row["recent_selected_count"]),
                "latest_date": fmt_date(op_row["latest_date"]),
                "latest_value": float(op_row["latest_score"]),
                "latest_selected": bool(op_row["latest_selected"]),
                "cutoff": float(op_row["cutoff"]),
                "last_selected_date": fmt_date(op_row["last_selected_date"]),
                "usage_note": (
                    f'Third-round deep-research line with round3_score={float(row["round3_score"]):.4f}; '
                    f'best rule avg_return={float(row["best_rule_avg_return"]):.4f} across {int(row["best_rule_trade_count"])} trades.'
                ),
            }
        )
    return pd.DataFrame(rows)


def build_followup_round4_status(asset_dir: Path) -> pd.DataFrame:
    decision_path = asset_dir / "followup_round4_decision_summary.tsv"
    operator_path = asset_dir / "followup_round4_operator_summary.tsv"
    if not decision_path.exists() or not operator_path.exists():
        raise FileNotFoundError(f"Missing round-4 follow-up files for {asset_dir.name}")
    decision = read_tsv(decision_path)
    operator = read_tsv(operator_path)
    rows: list[dict[str, object]] = []
    for idx, row in decision.iterrows():
        matches = operator.loc[
            (operator["model_name"] == row["model_name"]) & (operator["best_rule_name"] == row["best_rule_name"])
        ]
        op_row = matches.iloc[0] if not matches.empty else operator.loc[operator["model_name"] == row["model_name"]].iloc[0]
        rows.append(
            {
                "line_id": f'{row["model_name"]}::{row["best_rule_name"]}',
                "lane_type": "deep_research_round4",
                "role": "primary" if idx == 0 else "research_side_line",
                "preferred": idx == 0,
                "status": "watchlist_ready" if int(op_row["recent_selected_count"]) > 0 else "inactive",
                "recent_selected_count": int(op_row["recent_selected_count"]),
                "latest_date": fmt_date(op_row["latest_date"]),
                "latest_value": float(op_row["latest_score"]),
                "latest_selected": bool(op_row["latest_selected"]),
                "cutoff": float(op_row["cutoff"]),
                "last_selected_date": fmt_date(op_row["last_selected_date"]),
                "usage_note": (
                    f'Third-round benchmark-guardrail line with round4_score={float(row["round4_score"]):.4f}; '
                    f'best rule avg_return={float(row["best_rule_avg_return"]):.4f} across {int(row["best_rule_trade_count"])} trades.'
                ),
            }
        )
    return pd.DataFrame(rows)


def build_gld(asset_dir: Path) -> pd.DataFrame:
    config = ac.load_asset_config("gld")
    preferred_line = str(config.get("live_operator_line_id", "")).strip() or "gld_current_live_mixed_live"
    latest_prediction_path = ac.get_latest_prediction_path("gld")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing GLD latest prediction file: {latest_prediction_path}")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    explicit_line = str(payload.get("live_operator_line_id", "")).strip()
    live_provenance = cast(dict[str, object], payload.get("live_provenance", {}))
    provenance_line = str(live_provenance.get("operator_line_id", "")).strip()
    settings = ac.get_live_term_panic_settings("gld")
    signature = ac.get_live_mixed_signature("gld")
    decision_overlay = str(live_provenance.get("decision_overlay", "")).strip()
    term_panic_feature = str(live_provenance.get("term_panic_feature", "")).strip()
    term_panic_threshold = live_provenance.get("term_panic_threshold")
    expected_threshold = settings.get("threshold")
    signature_matches = (
        str(live_provenance.get("left_expert", "")).strip() == str(signature.get("left_expert", ""))
        and str(live_provenance.get("right_expert", "")).strip() == str(signature.get("right_expert", ""))
        and str(live_provenance.get("outer_gate_feature", "")).strip() == str(signature.get("outer_gate_feature", ""))
        and round(float(cast(float | int | str, live_provenance.get("outer_gate_threshold", 0.0))), 6)
        == round(float(cast(float | int | str, signature.get("outer_gate_threshold", 0.0))), 6)
    )
    overlay_matches = (
        decision_overlay == "vix_vxv_term_panic_block"
        and term_panic_feature == str(settings.get("feature", ""))
        and expected_threshold is not None
        and term_panic_threshold is not None
        and round(float(cast(float | int | str, term_panic_threshold)), 6)
        == round(float(cast(float | int | str, expected_threshold)), 6)
    )
    baseline_matches = decision_overlay == "" and term_panic_feature == "" and term_panic_threshold is None
    line_matches = False
    if preferred_line == "gld_mixed_vix_vxv_term_panic_live":
        line_matches = overlay_matches
    elif preferred_line == "gld_current_live_mixed_live":
        line_matches = baseline_matches
    if explicit_line != preferred_line or provenance_line != preferred_line or not signature_matches or not line_matches:
        raise ValueError(f"GLD preferred line '{preferred_line}' cannot be validated from live cache provenance.")
    rows = read_signal_rows_from_cache(latest_prediction_path.parent, "gld", 60)
    selected_rows = rows.loc[rows["signal"].astype(str) != "no_entry"]
    recent_selected_count = int(len(selected_rows))
    selected_dates = [str(value) for value in selected_rows["date"].tolist()]
    live_extra_features = tuple(str(name) for name in payload.get("model_extra_features", []) if str(name).strip())
    model_summary = payload.get("model_summary", {})
    reference_rule = str(model_summary.get("reference_percentile_rule", "top_20pct"))
    model_family = str(model_summary.get("model_family", "logistic"))
    live_label_mode = str(model_summary.get("label_mode", "drop-neutral"))
    live_decision_rule = str(model_summary.get("live_decision_rule", "threshold_plus_buy_point_overlay")).strip()
    latest_signal = str(payload.get("signal_summary", {}).get("signal", "no_entry"))
    latest_selected = latest_signal != "no_entry"
    if model_family == "hard_gate_two_expert_mixed":
        line_id = preferred_line
        feature_note = f"hard-gate mixed two-expert {live_label_mode} path"
    elif len(live_extra_features) > 2:
        line_id = "context_stack_live"
        feature_note = "context-stack extras"
    elif live_extra_features:
        line_id = "_".join(live_extra_features) + "_live"
        feature_note = " + ".join(live_extra_features)
    else:
        line_id = "gld_live_threshold_overlay"
        feature_note = "configured live extras"
    return pd.DataFrame(
        [
            {
                "line_id": line_id,
                "lane_type": "binary_operator",
                "role": "primary",
                "preferred": True,
                "status": "active" if latest_selected else "inactive",
                "recent_selected_count": recent_selected_count,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": latest_selected,
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": selected_dates[-1] if selected_dates else "",
                "usage_note": f"Current GLD live line uses {feature_note} with {live_decision_rule}; {reference_rule} remains the reference rule.",
            }
        ]
    )


BUILDERS["gld"] = build_gld


def build_slv(asset_dir: Path) -> pd.DataFrame:
    slv_preferences = get_slv_live_preferences()
    preferred_line = slv_preferences["preferred_line"]
    latest_prediction_path = ac.get_latest_prediction_path("slv")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing SLV latest prediction file: {latest_prediction_path}")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    if not slv_live_cache_matches_preferred_line(payload, slv_preferences):
        raise ValueError(f"SLV preferred line '{preferred_line}' cannot be validated from live cache provenance.")
    rows = read_signal_rows_from_cache(latest_prediction_path.parent, "slv", 60)
    validate_latest_signal_cache(payload, rows, "slv")
    selected_rows = rows.loc[rows["signal"].astype(str) != "no_entry"]
    recent_selected_count = int(len(selected_rows))
    signal = str(payload["signal_summary"]["signal"])
    benchmark_symbol = slv_preferences["benchmark_symbol"] or "benchmark"
    return pd.DataFrame(
        [
            {
                "line_id": preferred_line,
                "lane_type": "binary_operator",
                "role": "primary",
                "preferred": True,
                "status": "active" if signal != "no_entry" else "inactive",
                "recent_selected_count": recent_selected_count,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": signal != "no_entry",
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": fmt_date(selected_rows.iloc[-1]["date"]) if not selected_rows.empty else "",
                "usage_note": f"Primary SLV live line uses the adopted {benchmark_symbol}-relative hard-gate two-expert breakthrough.",
            }
        ]
    )


BUILDERS["slv"] = build_slv


def build_base_status(asset_dir: Path) -> pd.DataFrame:
    results_path = asset_dir / "results.tsv"
    latest_value = None
    cutoff = None
    latest_date = ""
    status = "research_only"
    usage_note = "Base research asset with no follow-up operating rounds yet."

    if results_path.exists():
        results = read_tsv(results_path)
        if not results.empty:
            row = latest_row(results)
            headline = row.get("headline_score")
            promotion_gate = row.get("promotion_gate")
            description = str(row.get("description", "")).strip()
            result_status = str(row.get("status", "")).strip()
            latest_value = _float_or_none(headline)
            cutoff = _float_or_none(promotion_gate)
            if result_status:
                status = result_status.lower().replace(" ", "_")
            if description:
                usage_note = description

    return pd.DataFrame(
        [
            {
                "line_id": "base_research",
                "lane_type": "research_backlog",
                "role": "research_primary",
                "preferred": True,
                "status": status,
                "recent_selected_count": 0,
                "latest_date": latest_date,
                "latest_value": latest_value,
                "latest_selected": False,
                "cutoff": cutoff,
                "last_selected_date": "",
                "usage_note": usage_note,
            }
        ]
    )


def main() -> None:
    asset_key = ac.get_asset_key()
    asset_dir = ac.get_asset_dir(asset_key)
    if asset_key in BUILDERS:
        output = BUILDERS[asset_key](asset_dir)
    elif (asset_dir / "followup_round4_decision_summary.tsv").exists() and (asset_dir / "followup_round4_operator_summary.tsv").exists():
        output = build_followup_round4_status(asset_dir)
    elif (asset_dir / "followup_round3_decision_summary.tsv").exists() and (asset_dir / "followup_round3_operator_summary.tsv").exists():
        output = build_followup_round3_status(asset_dir)
    elif (asset_dir / "followup_round2_decision_summary.tsv").exists() and (asset_dir / "followup_round2_operator_summary.tsv").exists():
        output = build_followup_round2_status(asset_dir)
    else:
        output = build_base_status(asset_dir)
    output_path = asset_dir / "active_status_summary.tsv"
    output.to_csv(output_path, sep="\t", index=False)
    preferred_mask = output["preferred"].fillna(False).astype(bool)
    print(
        json.dumps(
            {
                "asset_key": asset_key,
                "output_path": str(output_path),
                "rows": len(output),
                "preferred_line": str(output.loc[preferred_mask, "line_id"].iloc[0]) if bool(preferred_mask.any()) else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
