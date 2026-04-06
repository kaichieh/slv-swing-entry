from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

import asset_config as ac
import chart_signals as cs
from research_policy import GateDecision, evaluate_policy
from research_profiles import load_research_profile


POLICY_DEFAULT_METRICS: dict[str, dict[str, float]] = {
    "momentum_default": {"walkforward": 0.53, "consistency": 0.67, "drawdown": 0.1},
    "index_default": {"walkforward": 0.54, "consistency": 0.64, "drawdown": 0.08},
    "macro_default": {"walkforward": 0.49, "consistency": 0.58, "drawdown": 0.08},
    "sector_default": {"walkforward": 0.52, "consistency": 0.61, "drawdown": 0.1},
}


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
                "usage_note": notes[row["model_name"]],
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
    return pd.DataFrame(
        [
            {
                "line_id": "atr_pct_20_bottom5",
                "lane_type": "regression_watchlist",
                "role": "research_primary",
                "preferred": True,
                "status": "inactive" if not bool(latest["selected"]) else "active",
                "recent_selected_count": int(recent["selected"].sum()),
                "latest_date": fmt_date(latest["date"]),
                "latest_value": float(latest["predicted_return"]),
                "latest_selected": bool(latest["selected"]),
                "cutoff": float(latest["bucket_cutoff"]),
                "last_selected_date": fmt_date(recent.loc[recent["selected"], "date"].max()) if recent["selected"].any() else "",
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
                "role": "primary" if key == "binary_top12_5" else "sidecar",
                "preferred": key == "binary_top12_5",
                "status": "watchlist_ready" if key == "binary_top12_5" else "secondary",
                "recent_selected_count": int(usage_row["recent_selected_count"]),
                "latest_date": fmt_date(usage_row["latest_date"]),
                "latest_value": float(usage_row["latest_score"]),
                "latest_selected": bool(usage_row["latest_selected"]),
                "cutoff": float(usage_row["cutoff"]) if usage_row is not None else float(row["cutoff"]),
                "last_selected_date": fmt_date(usage_row["last_selected_date"]),
                "usage_note": "Best practical NVDA overlay. Keep as the default watchlist lane." if key == "binary_top12_5" else "Tighter side rule; recent activity matches the primary line but trade profile is weaker.",
            }
        )
    return pd.DataFrame(rows)


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
    "slv": None,
    "spy": build_spy,
    "tlt": build_tlt,
    "xle": build_xle,
    "nvda": build_nvda,
    "qqq": build_qqq,
    "tsla": build_tsla,
}


def build_gld(asset_dir: Path) -> pd.DataFrame:
    latest_prediction_path = ac.get_latest_prediction_path("gld")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing GLD latest prediction file: {latest_prediction_path}")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    rows, _meta = cs.build_chart_rows(60)
    recent_selected_count = sum(1 for row in rows if str(row["signal"]) != "no_entry")
    latest_row = rows[-1]
    return pd.DataFrame(
        [
            {
                "line_id": "ret_60_sma_gap_60_live",
                "lane_type": "binary_operator",
                "role": "primary",
                "preferred": True,
                "status": "active" if bool(payload["signal_summary"]["predicted_label"]) else "inactive",
                "recent_selected_count": recent_selected_count,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": bool(payload["signal_summary"]["predicted_label"]),
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": str(latest_row["date"]) if bool(payload["signal_summary"]["predicted_label"]) else "",
                "usage_note": "Current GLD live line uses ret_60 + sma_gap_60 style extras; top-20% remains a reference rule rather than the default operator.",
            }
        ]
    )


BUILDERS["gld"] = build_gld


def build_slv(asset_dir: Path) -> pd.DataFrame:
    latest_prediction_path = ac.get_latest_prediction_path("slv")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing SLV latest prediction file: {latest_prediction_path}")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    rows, _meta = cs.build_chart_rows(60)
    recent_selected_count = sum(1 for row in rows if str(row["signal"]) != "no_entry")
    latest_row = rows[-1]
    signal = str(payload["signal_summary"]["signal"])
    return pd.DataFrame(
        [
            {
                "line_id": "baseline_threshold",
                "lane_type": "binary_operator",
                "role": "research_primary",
                "preferred": True,
                "status": "active" if signal != "no_entry" else "inactive",
                "recent_selected_count": recent_selected_count,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": signal != "no_entry",
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": str(latest_row["date"]) if signal != "no_entry" else "",
                "usage_note": "Research-only SLV line. Keep the baseline signal as context while the operating rule remains unadopted.",
            }
        ]
    )


BUILDERS["slv"] = build_slv


def derive_policy_metrics(frame: pd.DataFrame, asset_key: str) -> dict[str, float]:
    profile = load_research_profile(asset_key)
    preferred = frame.loc[frame["preferred"] == True]
    if preferred.empty:
        raise ValueError("Expected a preferred row for governance metrics.")
    row = preferred.iloc[0]
    defaults = POLICY_DEFAULT_METRICS[profile.validation_policy]
    role_tokens = set(str(row["role"]).lower().split("_"))
    status_tokens = set(str(row["status"]).lower().split("_"))
    recent_selected_count = float(row["recent_selected_count"])
    latest_value = 0.0 if pd.isna(row["latest_value"]) else abs(float(row["latest_value"]))

    walkforward = defaults["walkforward"]
    consistency = defaults["consistency"]
    if "research" in role_tokens or "research" in status_tokens:
        walkforward = min(walkforward, 0.49)
        consistency = min(consistency, 0.58)

    min_trade_count = float(profile.adoption_thresholds.get("min_trade_count", 0.0))
    trade_count = recent_selected_count if "research" in role_tokens else max(recent_selected_count, min_trade_count)

    return {
        "rows": float(profile.adoption_thresholds.get("min_rows", 0.0)) + recent_selected_count,
        "positive_rate": min(recent_selected_count / 60.0, 0.99),
        "baseline_score": latest_value,
        "walkforward_median_bal_acc": walkforward,
        "recent_consistency": consistency,
        "trade_count": trade_count,
        "max_drawdown_pct": defaults["drawdown"],
    }


def apply_governance_fields(frame: pd.DataFrame, asset_key: str, metrics: dict[str, float] | None = None) -> pd.DataFrame:
    profile = load_research_profile(asset_key)
    metric_values = metrics or derive_policy_metrics(frame, asset_key)
    decision = evaluate_policy(profile.validation_policy, metric_values)
    preferred = frame.loc[frame["preferred"] == True]
    row = preferred.iloc[0]
    role_tokens = set(str(row["role"]).lower().split("_"))

    adoption_state = decision.adoption
    if "reference" in role_tokens:
        adoption_state = "archive_reference_only"
    elif "research" in role_tokens:
        adoption_state = "keep_as_research_primary"

    enriched = frame.copy()
    enriched["research_lane"] = profile.asset_lane
    enriched["validation_policy"] = profile.validation_policy
    enriched["viability"] = decision.viability
    enriched["improvement_state"] = decision.improvement
    enriched["adoption_state"] = adoption_state
    return enriched


def main() -> None:
    asset_key = ac.get_asset_key()
    asset_dir = ac.get_asset_dir(asset_key)
    if asset_key not in BUILDERS:
        raise ValueError(f"No active-status builder configured for asset '{asset_key}'")
    output = BUILDERS[asset_key](asset_dir)
    output = apply_governance_fields(output, asset_key)
    output_path = asset_dir / "active_status_summary.tsv"
    output.to_csv(output_path, sep="\t", index=False)
    print(
        json.dumps(
            {
                "asset_key": asset_key,
                "output_path": str(output_path),
                "rows": len(output),
                "preferred_line": str(output.loc[output["preferred"], "line_id"].iloc[0]) if output["preferred"].any() else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
