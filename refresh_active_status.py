from __future__ import annotations

import json
from pathlib import Path

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


def build_gld(asset_dir: Path) -> pd.DataFrame:
    latest_prediction_path = ac.get_latest_prediction_path("gld")
    if not latest_prediction_path.exists():
        raise FileNotFoundError(f"Missing GLD latest prediction file: {latest_prediction_path}")
    payload = json.loads(latest_prediction_path.read_text(encoding="utf-8"))
    rows, _meta = cs.build_chart_rows(60)
    recent_selected_count = sum(1 for row in rows if str(row["signal"]) != "no_entry")
    selected_dates = [str(row["date"]) for row in rows if str(row["signal"]) != "no_entry"]
    live_extra_features = tuple(str(name) for name in payload.get("model_extra_features", []) if str(name).strip())
    reference_rule = str(payload.get("model_summary", {}).get("reference_percentile_rule", "top_20pct"))
    if len(live_extra_features) > 2:
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
                "status": "active" if bool(payload["signal_summary"]["predicted_label"]) else "inactive",
                "recent_selected_count": recent_selected_count,
                "latest_date": str(payload["latest_raw_date"]),
                "latest_value": float(payload["signal_summary"]["predicted_probability"]),
                "latest_selected": bool(payload["signal_summary"]["predicted_label"]),
                "cutoff": float(payload["signal_summary"]["decision_threshold"]),
                "last_selected_date": selected_dates[-1] if selected_dates else "",
                "usage_note": f"Current GLD live line uses {feature_note} with the threshold-plus-buy-point overlay; {reference_rule} remains the reference rule.",
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


def main() -> None:
    asset_key = ac.get_asset_key()
    asset_dir = ac.get_asset_dir(asset_key)
    if asset_key in BUILDERS:
        output = BUILDERS[asset_key](asset_dir)
    else:
        output = build_followup_round2_status(asset_dir)
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
