"""
Render a local HTML chart of recent asset closes colored by live model signal.
"""

from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from typing import cast

import numpy as np
import pandas as pd

import asset_config as ac
import signal_chart_renderer
import train as tr
from predict_latest import (
    apply_buy_point_overlay,
    build_history_probabilities,
    build_feature_names,
    build_model_rationale,
    build_rule_rationale,
    classify_signal,
    fit_model,
    get_rule_top_pct,
    predict_probabilities,
    score_latest_row,
    summarize_rule,
)
from prepare import (
    BENCHMARK_SYMBOL,
    add_context_features,
    add_price_features,
    add_relative_strength_features,
    download_asset_prices,
    load_splits,
)

OUTPUT_PATH = str(ac.get_chart_output_path())
ROWS_OUTPUT_PATH = str(ac.get_cache_dir() / "signal_rows.tsv")
DEFAULT_LOOKBACK_DAYS = 5 * 252
SIGNAL_COLORS = {
    "no_entry": "#9ca3af",
    "weak_bullish": "#fde68a",
    "bullish": "#f59e0b",
    "strong_bullish": "#16a34a",
    "very_strong_bullish": "#065f46",
}


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    return int(value) if value is not None else default


def _normalize_default_chart_signal_mode(value: object) -> str:
    mode = str(value).strip().lower()
    return mode if mode in {"raw", "execution"} else "raw"


def _payload_raw_model_signal(payload: dict[str, object]) -> str:
    signal_summary = cast(dict[str, object], payload.get("signal_summary", {}))
    explicit_signal = str(signal_summary.get("raw_model_signal", "")).strip()
    if explicit_signal:
        return explicit_signal
    model_signal_summary = cast(dict[str, object], payload.get("model_signal_summary", {}))
    return str(model_signal_summary.get("signal", "")).strip()


def _rounded_payload_value(value: object, digits: int) -> float:
    return round(float(cast(float | int | str, value)), digits)


def _joined_payload_lines(value: object) -> str:
    if isinstance(value, list):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _apply_latest_prediction_overlay(latest_row: dict[str, object], payload: dict[str, object]) -> dict[str, object]:
    signal_summary = cast(dict[str, object], payload.get("signal_summary", {}))
    buy_point_summary = cast(dict[str, object], payload.get("buy_point_summary", {}))
    rule_summary = cast(dict[str, object], payload.get("rule_summary", {}))
    rationale_summary = cast(dict[str, object], payload.get("rationale_summary", {}))
    latest_feature_snapshot = cast(dict[str, object], payload.get("latest_feature_snapshot", {}))

    if payload.get("latest_raw_date") is not None:
        latest_row["date"] = str(payload["latest_raw_date"])
    if signal_summary.get("signal") is not None:
        latest_row["signal"] = str(signal_summary["signal"])

    raw_model_signal = _payload_raw_model_signal(payload)
    if raw_model_signal:
        latest_row["raw_model_signal"] = raw_model_signal
    if buy_point_summary.get("buy_point_ok") is not None:
        latest_row["buy_point_ok"] = bool(buy_point_summary["buy_point_ok"])
    if buy_point_summary.get("buy_point_warnings") is not None:
        latest_row["buy_point_warnings"] = _joined_payload_lines(buy_point_summary["buy_point_warnings"])
    if signal_summary.get("predicted_probability") is not None:
        latest_row["probability"] = _rounded_payload_value(signal_summary["predicted_probability"], 4)
    if signal_summary.get("decision_threshold") is not None:
        latest_row["threshold"] = _rounded_payload_value(signal_summary["decision_threshold"], 4)
    if signal_summary.get("confidence_gap") is not None:
        latest_row["confidence_gap"] = _rounded_payload_value(signal_summary["confidence_gap"], 4)
    if payload.get("latest_close") is not None:
        latest_row["close"] = _rounded_payload_value(payload["latest_close"], 2)
    if rule_summary.get("selected") is not None:
        latest_row["rule_selected"] = bool(rule_summary["selected"])
    if rule_summary.get("cutoff") is not None:
        latest_row["rule_cutoff"] = _rounded_payload_value(rule_summary["cutoff"], 4)
    if rule_summary.get("rule_name") is not None:
        latest_row["rule_name"] = str(rule_summary["rule_name"])
    if rule_summary.get("percentile_rank") is not None:
        latest_row["percentile_rank"] = _rounded_payload_value(rule_summary["percentile_rank"], 4)
    if rationale_summary.get("model_reasons") is not None:
        latest_row["model_rationale"] = _joined_payload_lines(rationale_summary["model_reasons"])
    if rationale_summary.get("rule_reason") is not None:
        latest_row["rule_rationale"] = str(rationale_summary["rule_reason"])

    for field_name, digits in {
        "ret_20": 4,
        "ret_60": 4,
        "drawdown_20": 4,
        "sma_gap_20": 4,
        "sma_gap_60": 4,
        "volume_vs_20": 4,
        "rsi_14": 2,
    }.items():
        if latest_feature_snapshot.get(field_name) is not None:
            latest_row[field_name] = _rounded_payload_value(latest_feature_snapshot[field_name], digits)
    return latest_row


def build_authoritative_latest_signal_row(
    latest_row: dict[str, object], payload: dict[str, object]
) -> dict[str, object]:
    return _apply_latest_prediction_overlay(dict(latest_row), payload)


def synchronize_latest_signal_row(
    rows: list[dict[str, object]], payload: dict[str, object] | None = None
) -> list[dict[str, object]]:
    synced_rows = [dict(row) for row in rows]
    if not synced_rows:
        return synced_rows

    effective_payload = payload
    if effective_payload is None:
        latest_prediction_path = Path(ac.get_latest_prediction_path())
        if not latest_prediction_path.exists():
            return synced_rows
        effective_payload = cast(dict[str, object], json.loads(latest_prediction_path.read_text(encoding="utf-8")))

    synced_rows[-1] = build_authoritative_latest_signal_row(synced_rows[-1], effective_payload)
    return synced_rows


def build_chart_rows(lookback_days: int) -> tuple[list[dict[str, object]], dict[str, object]]:
    tr.set_seed(tr.get_env_int("AR_SEED", tr.SEED))
    raw_prices = download_asset_prices()
    live_features = add_context_features(add_relative_strength_features(add_price_features(raw_prices), BENCHMARK_SYMBOL))
    splits = load_splits()
    feature_names = build_feature_names()
    model_artifacts = fit_model(splits, feature_names, raw_prices=raw_prices)
    feature_names = list(model_artifacts["feature_names"])
    threshold = float(model_artifacts["threshold"])
    history_probabilities = build_history_probabilities(model_artifacts, splits, feature_names)
    rule_top_pct = get_rule_top_pct()

    train_frame = model_artifacts["train_frame"]
    scored = live_features.dropna(subset=feature_names).copy()
    scored = scored.tail(lookback_days).reset_index(drop=True)

    rows: list[dict[str, object]] = []
    for idx in range(len(scored)):
        row = scored.iloc[[idx]]
        vector, snapshot = score_latest_row(model_artifacts, feature_names, train_frame, row)
        probability = float(predict_probabilities(model_artifacts, vector)[0])
        raw_signal, band_info = classify_signal(probability, float(threshold), history_probabilities)
        signal, buy_point_summary = apply_buy_point_overlay(raw_signal, snapshot)
        rule_info = summarize_rule(probability, history_probabilities, rule_top_pct)
        rationale_text = " | ".join(build_model_rationale(snapshot))
        rule_text = build_rule_rationale(probability, float(threshold), rule_info)
        buy_point_warnings = cast(list[str], buy_point_summary["buy_point_warnings"])
        rule_cutoff = float(cast(float | int | str, rule_info["cutoff"]))
        percentile_rank = float(cast(float | int | str, rule_info["percentile_rank"]))
        rows.append(
            {
                "date": row["date"].iloc[0].strftime("%Y-%m-%d"),
                "close": round(float(row["close"].iloc[0]), 2),
                "signal": signal,
                "raw_model_signal": raw_signal,
                "buy_point_ok": bool(buy_point_summary["buy_point_ok"]),
                "buy_point_warnings": " | ".join(buy_point_warnings),
                "probability": round(probability, 4),
                "threshold": round(float(threshold), 4),
                "confidence_gap": band_info["confidence_gap"],
                "rule_selected": bool(rule_info["selected"]),
                "rule_cutoff": round(rule_cutoff, 4),
                "rule_name": str(rule_info["rule_name"]),
                "percentile_rank": round(percentile_rank, 4),
                "model_rationale": rationale_text,
                "rule_rationale": rule_text,
                "ret_20": round(float(snapshot.get("ret_20", 0.0)), 4),
                "ret_60": round(float(snapshot.get("ret_60", 0.0)), 4),
                "drawdown_20": round(float(snapshot.get("drawdown_20", 0.0)), 4),
                "sma_gap_20": round(float(snapshot.get("sma_gap_20", 0.0)), 4),
                "volume_vs_20": round(float(snapshot.get("volume_vs_20", 0.0)), 4),
                "rsi_14": round(float(snapshot.get("rsi_14", 0.0)), 2),
            }
        )

    meta = {
        "threshold": round(float(threshold), 4),
        "latest_date": rows[-1]["date"] if rows else None,
        "lookback_days": lookback_days,
        "signal_colors": SIGNAL_COLORS,
        "rule_top_pct": rule_top_pct,
    }
    return rows, meta


def build_chart_payload(rows: list[dict[str, object]], meta: dict[str, object]) -> dict[str, object]:
    config = ac.load_asset_config()
    algorithm_name = str(config.get("live_model_family", config.get("model_family", "logistic")))
    label_mode = str(config.get("live_label_mode", config.get("label_mode", "drop-neutral")))
    default_chart_signal_mode = _normalize_default_chart_signal_mode(
        config.get("default_chart_signal_mode", "raw")
    )
    symbol = ac.get_asset_symbol()
    title = f"{symbol} {algorithm_name}"
    subtitle = (
        f"Generated date: {meta['latest_date']} · Latest date: {meta['latest_date']} · Lookback: {meta['lookback_days']}"
    )
    reference_rule = rows[-1]["rule_name"] if rows else f"top_{meta['rule_top_pct']:g}%_reference"

    return {
        "variant": "signal",
        "asset_key": ac.get_asset_key(),
        "symbol": symbol,
        "algorithm_name": algorithm_name,
        "algorithm_label": title,
        "model_family": algorithm_name,
        "label_mode": label_mode,
        "reference_rule": str(reference_rule),
        "default_chart_signal_mode": default_chart_signal_mode,
        "generated_date": meta["latest_date"],
        "title": title,
        "subtitle": subtitle,
        "latest_summary": {
            "latest_date": meta["latest_date"],
            "lookback_days": meta["lookback_days"],
        },
        "legend": meta["signal_colors"],
        "rows": rows,
    }


def build_html(rows: list[dict[str, object]], meta: dict[str, object]) -> str:
    return signal_chart_renderer.render_html(build_chart_payload(rows, meta))


def main() -> None:
    lookback_days = get_env_int("AR_CHART_LOOKBACK_DAYS", DEFAULT_LOOKBACK_DAYS)
    rows, meta = build_chart_rows(lookback_days)
    rows_for_output = synchronize_latest_signal_row(rows)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    pd.DataFrame(rows_for_output).to_csv(ROWS_OUTPUT_PATH, sep="\t", index=False)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(build_html(rows_for_output, meta))
    print(f"Saved chart to: {OUTPUT_PATH}")
    print(f"Saved rows to: {ROWS_OUTPUT_PATH}")
    print(f"Bars rendered: {len(rows)}")
    print(f"Latest date: {meta['latest_date']}")


if __name__ == "__main__":
    main()
